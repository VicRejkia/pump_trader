# FILE: ga_optimizer.py (Refactored)

"""
Genetic Algorithm Optimizer

Uses PyGAD library to optimize trading parameters based on backtesting results.
""" 
import os
import asyncio
import pygad
import numpy as np
import pandas as pd
from datetime import datetime, timedelta, timezone
import time
import json
import nest_asyncio # Import nest_asyncio

from logger import logger, setup_logging
from ga_config import (
    OPTIMIZABLE_PARAMETERS, POPULATION_SIZE, NUM_GENERATIONS,
    CROSSOVER_PROBABILITY, MUTATION_PROBABILITY, FITNESS_METRIC, FITNESS_GOAL,
    DATA_SPLIT, BACKTEST_INITIAL_CAPITAL,
    HISTORICAL_DATA_START_TS, HISTORICAL_DATA_END_TS # Import date range from config
)
from database_handler import DatabaseClient
from backtester import run_backtest # Import the refactored backtester

# Global variable to hold loaded historical data (to avoid reloading in fitness func)
# Structure: {'train': {'mint1': df1, 'mint2': df2}, 'validation': {...}, 'test': {...}}
historical_data_sets = {}
# Global variable for database client
db_client = None

nest_asyncio.apply() # Apply the patch


def ensure_datetime(dt):
    if isinstance(dt, datetime):
        return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)
    if isinstance(dt, str):
        return datetime.strptime(dt, "%Y-%m-%d").replace(tzinfo=timezone.utc)
    raise ValueError(f"Unsupported date format: {dt}")

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
        start_date = ensure_datetime(start_date_str)
        end_date = ensure_datetime(end_date_str)
        logger.info(f"Attempting to load data from {start_date} to {end_date}") 

        # 1. Get a list of mints with trades within the period as candidates
        #    More sophisticated filtering (volume, scores within period) could be added here
        #    by modifying the DB query or filtering post-fetch.
        logger.info("Fetching list of mints with trades in the specified period...")
        query_mints_in_period = """
            SELECT DISTINCT mint FROM v_trades
            WHERE timestamp >= $1 AND timestamp < $2;
        """ 
        active_mints_records = await db_client.pool.fetch(query_mints_in_period, start_date, end_date)
        if not active_mints_records:
             logger.error("No tokens found with trades in the specified period.")
             return False
        mints_to_load = [r['mint'] for r in active_mints_records] 
        logger.info(f"Found {len(mints_to_load)} unique mints with trades. Fetching detailed historical data...")

        # 2. Fetch historical data using the refactored DB handler function
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
            if df.empty or not isinstance(df.index, pd.DatetimeIndex):
                logger.warning(f"Skipping token {mint} due to empty data or invalid index.")
                continue

            # Ensure data exists before trying to slice
            if not df.index.min() < end_date or not df.index.max() >= start_date:
                 logger.warning(f"Token {mint} data does not overlap with requested date range after fetch. Skipping.")
                 continue


            df_train = df[df.index < train_end].copy()
            df_validation = df[(df.index >= train_end) & (df.index < validation_end)].copy()
            df_test = df[df.index >= validation_end].copy() 

            # Basic check for required columns after fetch and before adding to sets
            required_cols = ['price', 'volume', 'market_cap_calculated', 'rugcheck_score', 'socials_score']
            if not all(col in df.columns for col in required_cols):
                logger.warning(f"Token {mint} missing required columns after fetch. Skipping.")
                continue

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

        logger.info(f"Data split complete. Training tokens: {len(historical_data_sets['train'])}, Validation tokens: {len(historical_data_sets['validation'])}, Test tokens: {len(historical_data_sets['test'])}") 
        # Log sample data structure for verification
        if historical_data_sets['train']:
            sample_mint = list(historical_data_sets['train'].keys())[0]
            logger.debug(f"Sample training data columns for {sample_mint}: {historical_data_sets['train'][sample_mint].columns}")
            logger.debug(f"Sample training data head for {sample_mint}:\n{historical_data_sets['train'][sample_mint].head()}")

        return True

    except ValueError as ve:
        logger.error(f"Date parsing error: {ve}. Ensure dates are in YYYY-MM-DD format.")
        return False
    except Exception as e:
        logger.exception(f"Error during data loading/splitting: {e}")
        return False


# --- Fitness Function ---

async def run_backtest_for_fitness(solutions, data_set_key='train'):
    """
    Helper async function to run backtests for a batch of solutions on a specific dataset.
    Args:
        solutions: List of solutions (each solution is a list of parameters).
        data_set_key: String key ('train', 'validation', 'test') indicating which dataset to use.
    Returns:
        List of fitness values corresponding to each solution.
    """
    fitness_results = []
    logger.debug(f"Running backtests on '{data_set_key}' dataset for {len(solutions)} solutions.")

    # Select the appropriate dataset
    data_for_backtest = historical_data_sets.get(data_set_key, {})
    if not data_for_backtest:
        logger.error(f"No data found for dataset key '{data_set_key}'. Cannot calculate fitness.")
        # Return worst fitness for all solutions if dataset is missing
        worst_fitness = -float('inf') if FITNESS_GOAL == 'max' else float('inf')
        return [worst_fitness] * len(solutions)

    tasks_to_run = []
    solution_indices = [] # Keep track of which solution each task belongs to

    # Prepare all backtest tasks for all solutions and all tokens in the selected dataset
    for sol_idx, solution in enumerate(solutions):
        parameters = {param['name']: solution[i] for i, param in enumerate(OPTIMIZABLE_PARAMETERS)}
        for mint, df_data in data_for_backtest.items():
            if df_data.empty:
                logger.warning(f"Skipping backtest for {mint} (solution {sol_idx}) on '{data_set_key}' due to empty dataframe.")
                continue
            # Important: Pass copies of data and params to avoid modification issues
            tasks_to_run.append(run_backtest(parameters.copy(), df_data.copy(), BACKTEST_INITIAL_CAPITAL))
            solution_indices.append(sol_idx)

    if not tasks_to_run:
        logger.warning(f"No backtest tasks created for dataset '{data_set_key}'.")
        worst_fitness = -float('inf') if FITNESS_GOAL == 'max' else float('inf')
        return [worst_fitness] * len(solutions)

    # Run all backtests concurrently
    logger.info(f"Executing {len(tasks_to_run)} backtest tasks concurrently for {len(solutions)} solutions on '{data_set_key}' data...")
    start_batch_time = time.time()
    backtest_raw_results = await asyncio.gather(*tasks_to_run, return_exceptions=True)
    end_batch_time = time.time()
    logger.info(f"Finished {len(tasks_to_run)} backtests in {end_batch_time - start_batch_time:.2f} seconds.")


    # Aggregate results per solution
    aggregated_fitness = {i: {'total': 0.0, 'count': 0} for i in range(len(solutions))}

    for i, result in enumerate(backtest_raw_results):
        original_sol_idx = solution_indices[i]
        if isinstance(result, Exception):
            logger.error(f"Backtest task failed for solution {original_sol_idx} on '{data_set_key}': {result}")
            continue # Skip failed backtests
        elif isinstance(result, dict):
            fitness_value = result.get(FITNESS_METRIC)
            if fitness_value is None or pd.isna(fitness_value):
                logger.warning(f"Backtest result for solution {original_sol_idx} on '{data_set_key}' returned invalid fitness metric '{FITNESS_METRIC}': {fitness_value}. Skipping.")
                continue # Skip results without a valid fitness metric 
            aggregated_fitness[original_sol_idx]['total'] += fitness_value
            aggregated_fitness[original_sol_idx]['count'] += 1
        else:
            logger.warning(f"Unexpected backtest result type for solution {original_sol_idx} on '{data_set_key}': {type(result)}")

    # Calculate final average fitness for each solution
    for sol_idx in range(len(solutions)):
        total = aggregated_fitness[sol_idx]['total']
        count = aggregated_fitness[sol_idx]['count']
        if count == 0:
            logger.warning(f"No backtests completed successfully for solution {sol_idx} on '{data_set_key}'. Assigning worst fitness.")
            avg_fitness = -float('inf') if FITNESS_GOAL == 'max' else float('inf') # Worst fitness 
        else:
            avg_fitness = total / count
            logger.debug(f"Solution {sol_idx} evaluated on '{data_set_key}'. Average {FITNESS_METRIC}: {avg_fitness:.4f} across {count} tokens.") 
        fitness_results.append(avg_fitness)

    return fitness_results


def fitness_func_wrapper(ga_instance, solution, sol_idx):
    """
    PyGAD fitness function wrapper. Calls the async helper to run backtests.
    Uses the 'train' dataset by default.
    """ 
    start_time = time.time()
    # logger.debug(f"Evaluating solution index: {sol_idx}") # Reduce log noise

    fitness = -float('inf') if FITNESS_GOAL == 'max' else float('inf') # Default worst fitness

    try:
        # Run the async helper function for the single solution using asyncio.run()
        # This evaluates the solution against the 'train' dataset
        results = asyncio.run(run_backtest_for_fitness([solution], data_set_key='train'))

        if results and len(results) > 0:
            fitness = results[0] 
            # Handle potential None or NaN from the backtest result itself
            if fitness is None or pd.isna(fitness):
                 logger.warning(f"Backtest result for solution {sol_idx} was None or NaN after helper. Assigning worst fitness.")
                 fitness = -float('inf') if FITNESS_GOAL == 'max' else float('inf') 
        else:
            logger.warning(f"run_backtest_for_fitness returned invalid results for solution {sol_idx}. Assigning worst fitness.") 
            fitness = -float('inf') if FITNESS_GOAL == 'max' else float('inf')

    except Exception as e:
        # Catch any exception during asyncio.run or backtest execution
        logger.exception(f"Error running backtest within fitness function for solution {sol_idx}: {e}")
        fitness = -float('inf') if FITNESS_GOAL == 'max' else float('inf') # Assign worst fitness

    end_time = time.time()
    # logger.debug(f"Solution {sol_idx} evaluation took {end_time - start_time:.2f} seconds. Fitness: {fitness}") # Reduce log noise 

    # PyGAD expects a single fitness value. Higher is better for maximization.
    # Handle NaN/inf explicitly before returning
    if pd.isna(fitness) or fitness == -float('inf') or fitness == float('inf'):
         return -1e10 # Return a very small number for maximization if fitness is invalid

    # If minimizing, PyGAD maximizes 1/fitness (or handles negative values appropriately based on config)
    # We return the direct metric value, PyGAD handles the goal internally based on fitness_func definition
    return fitness # Return the calculated average fitness


# --- GA Execution ---

async def main():
    global db_client
    setup_logging() # Initialize logger

    # --- Database Connection ---
    db_client = DatabaseClient()
    try:
        await db_client.connect()
        # await db_client.init_db() # Schema should be initialized by main bot
    except Exception as e:
        logger.critical(f"Failed to connect to database: {e}") 
        return # Cannot proceed without DB

     # --- Load Data ---
    # Read dates from ga_config.py directly
    start_date_str = HISTORICAL_DATA_START_TS # Use imported config value
    end_date_str = HISTORICAL_DATA_END_TS     # Use imported config value

    logger.info(f"Using data range from config: {start_date_str} to {end_date_str}") # Log the used dates

    if not await load_and_split_data(start_date_str, end_date_str):
        logger.critical("Failed to load or split data. Exiting.") # cite: 326
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
        if 'values' in param:
            gene_space.append(param['values'])
        else:
            gene_space.append({'low': param['low'], 'high': param['high']})
        gene_type.append(param['type'])

    # Define callback for generation completion
    def on_generation(ga_instance):
        generation = ga_instance.generations_completed
        best_fitness = ga_instance.best_solution(pop_fitness=ga_instance.last_generation_fitness)[1]
        logger.info(f"Generation {generation} finished. Best Fitness: {best_fitness:.4f}")
        # Optionally save progress here (e.g., save best solution so far)
        # solution, _, _ = ga_instance.best_solution()
        # best_params = {param['name']: solution[i] for i, param in enumerate(OPTIMIZABLE_PARAMETERS)}
        # print(f"Best solution after gen {generation}: {best_params}")
        if generation % 10 == 0: # Log best solution every 10 generations
             solution, _, _ = ga_instance.best_solution(pop_fitness=ga_instance.last_generation_fitness)
             best_params_so_far = {param['name']: solution[i] for i, param in enumerate(OPTIMIZABLE_PARAMETERS)}
             logger.info(f"Best solution @ Gen {generation}: Fitness={best_fitness:.4f}, Params={json.dumps(best_params_so_far)}")


    logger.info(f"Setting up PyGAD: Pop={POPULATION_SIZE}, Gens={NUM_GENERATIONS}, Genes={len(OPTIMIZABLE_PARAMETERS)}")
    ga_instance = pygad.GA(
        num_generations=NUM_GENERATIONS,
        num_parents_mating=int(POPULATION_SIZE * 0.25), # Example: 25% parents mate
        fitness_func=fitness_func_wrapper, # Use the wrapper
        sol_per_pop=POPULATION_SIZE,
        num_genes=len(OPTIMIZABLE_PARAMETERS),
        gene_space=gene_space, 
        gene_type=gene_type, 
        parent_selection_type="sss", # Steady-state selection 
        crossover_type="single_point", 
        crossover_probability=CROSSOVER_PROBABILITY,
        mutation_type="random", 
        mutation_probability=MUTATION_PROBABILITY,
        mutation_by_replacement=True, # Recommended for random mutation
        keep_elitism=2, # Keep the best 2 solutions from previous generation 
        on_generation=on_generation,
        parallel_processing=None # Keep sequential for simplicity with asyncio.run
        # stop_criteria=["saturate_10"] # Example: Stop if fitness doesn't improve for 10 gens
    )

    # --- Run GA ---
    logger.info("Starting Genetic Algorithm optimization...")
    start_ga_time = time.time()
    try:
        ga_instance.run()
    except Exception as ga_err:
        logger.exception(f"Error during GA execution: {ga_err}")
        # Optionally try to save results even if GA run fails partially
    finally:
        end_ga_time = time.time()
        logger.info(f"GA optimization finished or stopped after {end_ga_time - start_ga_time:.2f} seconds.")


    # --- Results ---
    # Ensure results are accessed safely, especially if GA failed
    if hasattr(ga_instance, 'best_solution_generation') and ga_instance.best_solution_generation != -1:
        solution, solution_fitness, solution_idx = ga_instance.best_solution()
        logger.info(f"Best solution found (Fitness = {solution_fitness}):")
        best_params = {param['name']: solution[i] for i, param in enumerate(OPTIMIZABLE_PARAMETERS)}
        logger.info(json.dumps(best_params, indent=4)) 

        # --- Phase: Validation ---
        logger.info("Running validation on the best solution...")
        validation_fitness = -float('inf') if FITNESS_GOAL == 'max' else float('inf') # Default worst
        if historical_data_sets.get('validation'):
            try:
                # Use the async helper with the 'validation' dataset key
                validation_results = await run_backtest_for_fitness([solution], data_set_key='validation') # Await the async helper
                if validation_results and len(validation_results) > 0:
                    validation_fitness = validation_results[0] 
                    if validation_fitness is None or pd.isna(validation_fitness):
                        logger.warning("Validation run returned None/NaN fitness.")
                        validation_fitness = -float('inf') if FITNESS_GOAL == 'max' else float('inf')
                logger.info(f"Validation Fitness ({FITNESS_METRIC}): {validation_fitness}") 
            except Exception as e:
                logger.exception(f"Error during validation run: {e}")
        else:
            logger.warning("No validation data set found. Skipping validation.") 

        # --- Phase: Final Testing ---
        logger.info("Running final test on the best solution...")
        test_fitness = -float('inf') if FITNESS_GOAL == 'max' else float('inf') # Default worst
        if historical_data_sets.get('test'):
            try:
                 # Use the async helper with the 'test' dataset key
                test_results = await run_backtest_for_fitness([solution], data_set_key='test') # Await the async helper
                if test_results and len(test_results) > 0:
                    test_fitness = test_results[0] 
                    if test_fitness is None or pd.isna(test_fitness):
                        logger.warning("Test run returned None/NaN fitness.") 
                        test_fitness = -float('inf') if FITNESS_GOAL == 'max' else float('inf')
                logger.info(f"Test Fitness ({FITNESS_METRIC}): {test_fitness}") 
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
            'test_fitness': test_fitness,
            'ga_config': {
                'population_size': POPULATION_SIZE,
                'num_generations': NUM_GENERATIONS,
                'crossover_probability': CROSSOVER_PROBABILITY,
                'mutation_probability': MUTATION_PROBABILITY,
                'fitness_metric': FITNESS_METRIC,
                'fitness_goal': FITNESS_GOAL,
                'data_split': DATA_SPLIT,
                'backtest_initial_capital': BACKTEST_INITIAL_CAPITAL,
                'data_start_date': HISTORICAL_DATA_START_TS, # Use config dates
                'data_end_date': HISTORICAL_DATA_END_TS # Use config dates
             }, 
            'optimizable_parameters_config': OPTIMIZABLE_PARAMETERS 
        }
        try:
            # Convert numpy types to standard Python types for JSON serialization
            def convert_numpy_types(obj):
                if isinstance(obj, np.integer):
                    return int(obj)
                elif isinstance(obj, np.floating):
                    return float(obj) 
                elif isinstance(obj, np.ndarray):
                    return obj.tolist() 
                elif isinstance(obj, (datetime, pd.Timestamp)):
                     return obj.isoformat()
                # Add handling for potential inf/-inf
                elif obj == float('inf'):
                    return 'Infinity'
                elif obj == float('-inf'):
                    return '-Infinity'
                return obj

            with open(results_filename, 'w') as f:
                json.dump(results_data, f, indent=4, default=convert_numpy_types) 
            logger.info(f"Saved GA results to {results_filename}")
        except Exception as e:
            logger.error(f"Failed to save results to JSON: {e}")

        # Plot fitness graph
        try:
            save_dir = os.path.join(os.getcwd(), "ga_fitness_plot.png") # Ensure save dir exists or use absolute path
            ga_instance.plot_fitness(title="PyGAD Fitness Progress", save_dir=save_dir)
            logger.info(f"Saved fitness plot to {save_dir}")
        except Exception as e:
            logger.error(f"Failed to save fitness plot: {e}") 

    else:
         logger.error("GA did not complete successfully. No best solution found.")


    # --- Cleanup ---
    await db_client.close()
    logger.info("Optimizer finished.")


if __name__ == "__main__":
    # Use asyncio.run() to execute the async main function
    asyncio.run(main())