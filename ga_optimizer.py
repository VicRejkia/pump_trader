"""
Genetic Algorithm Optimizer

Uses PyGAD library to optimize trading parameters based on backtesting results.
"""

import asyncio
import pygad
import numpy as np
import pandas as pd
from datetime import datetime, timedelta, timezone
import time
import json

from logger import logger, setup_logging
from ga_config import (
    OPTIMIZABLE_PARAMETERS, POPULATION_SIZE, NUM_GENERATIONS,
    CROSSOVER_PROBABILITY, MUTATION_PROBABILITY, FITNESS_METRIC, FITNESS_GOAL,
    DATA_SPLIT, BACKTEST_INITIAL_CAPITAL # Add HISTORICAL_DATA_START_DATE, HISTORICAL_DATA_END_DATE if defined
)
from database_handler import DatabaseClient
from backtester import run_backtest

# Global variable to hold loaded historical data (to avoid reloading in fitness func)
# Structure: {'train': {'mint1': df1, 'mint2': df2}, 'validation': {...}, 'test': {...}}
historical_data_sets = {}
# Global variable for database client
db_client = None

# --- Data Preparation ---

async def load_and_split_data(start_date_str: str, end_date_str: str):
    """
    Loads historical data for all relevant tokens and splits it into
    training, validation, and test sets based on ga_config.DATA_SPLIT.

    Args:
        start_date_str: Start date string (YYYY-MM-DD).
        end_date_str: End date string (YYYY-MM-DD).

    Returns:
        bool: True if data loading and splitting was successful, False otherwise.
    """
    global historical_data_sets, db_client
    if not db_client:
        logger.error("Database client not initialized.")
        return False

    try:
        start_date = datetime.strptime(start_date_str, "%Y-%m-%d").replace(tzinfo=timezone.utc)
        start_date = datetime.strptime(start_date_str, "%Y-%m-%d").replace(tzinfo=timezone.utc)
        end_date = datetime.strptime(end_date_str, "%Y-%m-%d").replace(tzinfo=timezone.utc)
        logger.info(f"Attempting to load data from {start_date} to {end_date}")

        # 1. Get a *filtered* list of relevant mints first
        #    Use criteria to select tokens likely to be interesting for backtesting
        #    within the specified date range. Adjust criteria as needed.
        logger.info("Fetching filtered list of relevant mints for the period...")
        # Example criteria (adjust thresholds as needed):
        min_volume_sol_period = 10 # Min total SOL volume during the period
        max_rugcheck_score = 900
        max_socials_score = 90
        # We need a function similar to get_filtered_tokens but adapted for a date range
        # Let's reuse parts of find_trading_opportunities logic conceptually for filtering
        # NOTE: This requires adding/modifying a DB function or doing more complex filtering here.
        # For now, let's fetch tokens active *within* the period with some basic checks.
        # A simpler approach for now: Get tokens with trades within the period.
        query_mints_in_period = """
            SELECT DISTINCT mint FROM v_trades
            WHERE timestamp >= $1 AND timestamp < $2;
        """
        active_mints_records = await db_client.pool.fetch(query_mints_in_period, start_date, end_date)
        if not active_mints_records:
             logger.error("No tokens found with trades in the specified period.")
             return False
        mints_to_load = [r['mint'] for r in active_mints_records]
        logger.info(f"Found {len(mints_to_load)} unique mints with trades in the period. Fetching detailed data...")
        # TODO: Add more sophisticated filtering here (e.g., min volume, scores) if needed

        # 2. Fetch historical data *only* for these filtered mints
        all_historical_data = await db_client.get_historical_data_for_backtesting(mints_to_load, start_date, end_date)

        if not all_historical_data:
            logger.error("Failed to fetch any historical data for the specified mints and date range.")
            return False

        logger.info(f"Successfully fetched data for {len(all_historical_data)} tokens.")

        # 3. Split data chronologically for each token
        historical_data_sets = {'train': {}, 'validation': {}, 'test': {}}
        total_duration = end_date - start_date
        train_end = start_date + total_duration * DATA_SPLIT['training']
        validation_end = train_end + total_duration * DATA_SPLIT['validation']

        for mint, df in all_historical_data.items():
            if df.empty:
                continue

            df_train = df[df.index < train_end]
            df_validation = df[(df.index >= train_end) & (df.index < validation_end)]
            df_test = df[df.index >= validation_end]

            # Only include tokens that have data in the training set
            if not df_train.empty:
                historical_data_sets['train'][mint] = df_train
                if not df_validation.empty:
                    historical_data_sets['validation'][mint] = df_validation
                if not df_test.empty:
                    historical_data_sets['test'][mint] = df_test

        if not historical_data_sets['train']:
             logger.error("No tokens had sufficient data for the training period.")
             return False

        logger.info(f"Data split complete. Training tokens: {len(historical_data_sets['train'])}, "
                    f"Validation tokens: {len(historical_data_sets['validation'])}, "
                    f"Test tokens: {len(historical_data_sets['test'])}")
        return True

    except Exception as e:
        logger.exception(f"Error during data loading/splitting: {e}")
        return False


# --- Fitness Function ---

# Using asyncio.run inside the fitness function is simple but potentially slow
# as it creates/destroys an event loop for each evaluation.
# For large populations/generations, consider optimizing this (e.g., running
# backtests for the whole population concurrently outside the PyGAD loop if possible,
# or using a shared event loop with careful management).

async def run_backtest_for_fitness(solution):
    """Helper async function to run backtests for a given solution."""
    parameters = {param['name']: solution[i] for i, param in enumerate(OPTIMIZABLE_PARAMETERS)}
    total_fitness = 0.0
    num_tokens_backtested = 0

    tasks = []
    for mint, df_train in historical_data_sets.get('train', {}).items():
        # Create a task for each token's backtest
        tasks.append(run_backtest(parameters.copy(), df_train.copy(), BACKTEST_INITIAL_CAPITAL))

    if not tasks:
        logger.warning("No training data available for any token to run backtest.")
        return 0.0 # Return worst fitness if no data

    backtest_results = await asyncio.gather(*tasks, return_exceptions=True)

    for result in backtest_results:
        if isinstance(result, Exception):
            logger.error(f"Backtest failed for a token: {result}")
            # Penalize fitness heavily for errors? Or just ignore? Let's ignore for now.
            continue
        elif isinstance(result, dict):
            # Aggregate fitness (e.g., sum of PnL, average Sharpe)
            # Using FITNESS_METRIC from ga_config
            fitness_value = result.get(FITNESS_METRIC, 0.0)
            total_fitness += fitness_value
            num_tokens_backtested += 1
        else:
             logger.warning(f"Unexpected backtest result type: {type(result)}")


    if num_tokens_backtested == 0:
        logger.warning("No backtests completed successfully for this solution.")
        return 0.0 # Or negative infinity if maximizing

    # Average the fitness metric across all successfully backtested tokens
    average_fitness = total_fitness / num_tokens_backtested
    logger.debug(f"Solution evaluated. Average {FITNESS_METRIC}: {average_fitness:.4f} across {num_tokens_backtested} tokens.")
    return average_fitness


def fitness_func(ga_instance, solution, sol_idx):
    """
    PyGAD fitness function wrapper. Runs the backtest simulation for a given
    set of parameters (solution) using the training dataset.
    """
    start_time = time.time()
    logger.debug(f"Evaluating solution index: {sol_idx}")

    # Run the async backtest helper
    try:
        # Ensure an event loop is available or create one
        loop = asyncio.get_event_loop()
        logger.debug(f"Is event loop running? {asyncio.get_event_loop().is_running()}")
        if loop.is_running():
             # If running in an environment like Jupyter, need careful handling.
             # For simple script execution, asyncio.run might be okay here,
             # but let's try running in the existing loop if possible.
             # This part might need adjustment based on execution context.
             # Using asyncio.run() is simpler for standalone scripts.
             fitness = asyncio.run(run_backtest_for_fitness(solution))
        else:
             fitness = loop.run_until_complete(run_backtest_for_fitness(solution))

    except RuntimeError as e:
         # Fallback if get_event_loop causes issues or no loop exists
         logger.warning(f"RuntimeError getting event loop ({e}), falling back to asyncio.run().")
         try:
            #fitness = asyncio.run(run_backtest_for_fitness(solution))
            fitness = loop.run_until_complete(run_backtest_for_fitness(solution))
         except Exception as inner_e:
             logger.exception(f"Error running backtest within fitness function (asyncio.run): {inner_e}")
             fitness = -float('inf') if FITNESS_GOAL == 'max' else float('inf') # Worst possible fitness

    except Exception as e:
        logger.exception(f"Error running backtest within fitness function for solution {sol_idx}: {e}")
        fitness = -float('inf') if FITNESS_GOAL == 'max' else float('inf') # Worst possible fitness

    end_time = time.time()
    logger.debug(f"Solution {sol_idx} evaluation took {end_time - start_time:.2f} seconds. Fitness: {fitness}")

    # PyGAD maximizes fitness by default. If we want to minimize (e.g., drawdown),
    # return the negative or inverse of the value.
    if FITNESS_GOAL == 'min':
        # Avoid division by zero if fitness is 0
        return 1.0 / (fitness + 1e-9) if fitness >= 0 else -fitness # Example for minimization

    return fitness


# --- GA Execution ---

async def main():
    global db_client
    setup_logging() # Initialize logger

    # --- Database Connection ---
    db_client = DatabaseClient()
    try:
        await db_client.connect()
        await db_client.init_db() # Ensure schema exists
    except Exception as e:
        logger.critical(f"Failed to connect to database or initialize schema: {e}")
        return # Cannot proceed without DB

    # --- Load Data ---
    # TODO: Get actual date range from config or command line args
    start_date_str = "2025-04-09" # Example Start Date
    end_date_str = "2025-04-10"   # Example End Date
    if not await load_and_split_data(start_date_str, end_date_str):
        logger.critical("Failed to load or split data. Exiting.")
        await db_client.close()
        return

    if not historical_data_sets.get('train'):
        logger.critical("No training data loaded. Cannot run GA. Exiting.")
        await db_client.close()
        return

    logger.info("Data loaded and split successfully. Proceeding with GA setup.")


    # --- PyGAD Configuration ---
    gene_space = []
    gene_type = []
    for param in OPTIMIZABLE_PARAMETERS:
        space = {'low': param['low'], 'high': param['high']}
        # PyGAD uses step= for float precision sometimes, but range is usually enough
        # if param['type'] == float:
        #     space['step'] = (param['high'] - param['low']) / 1000 # Example step
        gene_space.append(space)
        gene_type.append(param['type'])

    # Define callback for generation completion
    def on_generation(ga_instance):
        logger.info(f"Generation {ga_instance.generations_completed} finished.")
        logger.info(f"Best fitness in generation: {ga_instance.best_solution()[1]}")
        # Optionally save progress here

    ga_instance = pygad.GA(
        num_generations=NUM_GENERATIONS,
        num_parents_mating=int(POPULATION_SIZE * 0.2), # Example: 20% parents mate
        fitness_func=fitness_func,
        sol_per_pop=POPULATION_SIZE,
        num_genes=len(OPTIMIZABLE_PARAMETERS),
        gene_space=gene_space,
        gene_type=gene_type,
        parent_selection_type="sss", # Steady-state selection
        crossover_type="single_point",
        crossover_probability=CROSSOVER_PROBABILITY,
        mutation_type="random",
        mutation_probability=MUTATION_PROBABILITY,
        # mutation_by_replacement=True, # Consider this for random mutation
        # random_mutation_min_val/max_val can be set per gene if needed, but gene_space handles ranges
        keep_elitism=1, # Keep the best solution from previous generation
        on_generation=on_generation,
        # parallel_processing=None # Can explore later if needed ('thread' or 'process')
        # stop_criteria=["saturate_10"] # Example: Stop if fitness doesn't improve for 10 gens
    )

    # --- Run GA ---
    logger.info("Starting Genetic Algorithm optimization...")
    start_ga_time = time.time()
    ga_instance.run()
    end_ga_time = time.time()
    logger.info(f"GA optimization finished in {end_ga_time - start_ga_time:.2f} seconds.")

    # --- Results ---
    solution, solution_fitness, solution_idx = ga_instance.best_solution()
    logger.info(f"Best solution found (Fitness = {solution_fitness}):")
    best_params = {param['name']: solution[i] for i, param in enumerate(OPTIMIZABLE_PARAMETERS)}
    logger.info(json.dumps(best_params, indent=4))

    # --- Phase 4: Validation (Placeholder) ---
    logger.info("Running validation on the best solution...")
    validation_fitness = 0.0
    if historical_data_sets.get('validation'):
         # Similar structure to fitness func, but run on validation set
         # Re-running the async helper function
         try:
             validation_fitness = await run_backtest_for_fitness(solution) # Pass the best solution
             logger.info(f"Validation Fitness ({FITNESS_METRIC}): {validation_fitness}")
         except Exception as e:
             logger.exception(f"Error during validation run: {e}")
    else:
        logger.warning("No validation data set found. Skipping validation.")

    # --- Phase 4: Final Testing (Placeholder) ---
    logger.info("Running final test on the best solution...")
    test_fitness = 0.0
    if historical_data_sets.get('test'):
         # Similar structure, run on test set
         try:
             # Need to adapt run_backtest_for_fitness or create a variant for test set
             # For now, just logging placeholder
             logger.info("Test run placeholder...") # Replace with actual test run
             # test_fitness = await run_backtest_on_set(solution, historical_data_sets['test'])
             # logger.info(f"Test Fitness ({FITNESS_METRIC}): {test_fitness}")
         except Exception as e:
             logger.exception(f"Error during test run: {e}")

    else:
        logger.warning("No test data set found. Skipping final test.")


    # --- Save Results ---
    results_filename = f"ga_results_{datetime.now():%Y%m%d_%H%M%S}.json"
    results_data = {
        'best_solution_parameters': best_params,
        'best_solution_fitness_training': solution_fitness,
        'validation_fitness': validation_fitness,
        'test_fitness': test_fitness, # Add test fitness if calculated
        'ga_config': {
            'population_size': POPULATION_SIZE,
            'num_generations': NUM_GENERATIONS,
            'crossover_probability': CROSSOVER_PROBABILITY,
            'mutation_probability': MUTATION_PROBABILITY,
            'fitness_metric': FITNESS_METRIC,
            'fitness_goal': FITNESS_GOAL,
            'data_split': DATA_SPLIT,
            'backtest_initial_capital': BACKTEST_INITIAL_CAPITAL,
            'data_start_date': start_date_str,
            'data_end_date': end_date_str
        },
        'optimizable_parameters_config': OPTIMIZABLE_PARAMETERS
    }
    try:
        with open(results_filename, 'w') as f:
            json.dump(results_data, f, indent=4)
        logger.info(f"Saved GA results to {results_filename}")
    except Exception as e:
        logger.error(f"Failed to save results to JSON: {e}")

    # Plot fitness graph
    ga_instance.plot_fitness(title="PyGAD Fitness Progress", save_dir="ga_fitness_plot.png")

    # --- Cleanup ---
    await db_client.close()
    logger.info("Optimizer finished.")


if __name__ == "__main__":
    asyncio.run(main())