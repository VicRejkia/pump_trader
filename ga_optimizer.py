import os
import asyncio
import pygad
import numpy as np
import pandas as pd
from datetime import datetime, timezone
import time
import json
# Import Pool, cpu_count, AND freeze_support
from multiprocessing import Pool, cpu_count, freeze_support
from itertools import islice

from logger import logger, setup_logging
from ga_config import (
    OPTIMIZABLE_PARAMETERS, POPULATION_SIZE, NUM_GENERATIONS,
    CROSSOVER_PROBABILITY, MUTATION_PROBABILITY, FITNESS_METRIC, FITNESS_GOAL,
    DATA_SPLIT, BACKTEST_INITIAL_CAPITAL,
    HISTORICAL_DATA_START_TS, HISTORICAL_DATA_END_TS
)
from database_handler import DatabaseClient
from backtester import run_backtest
from utils import load_and_split_data
import traceback # <-- Add traceback import

# Global variables (Keep them here if needed globally by functions)
db_client = None
historical_data_sets = {}
pool = None # Initialize pool as None globally


# --- Update Fitness Function Helper ---

def run_backtest_sync(task_data):
    """Synchronous wrapper for run_backtest suitable for multiprocessing."""
    logger.debug(f"run_backtest_sync called with task_data: {task_data}")
    solution_idx, parameters, mint, df_data, initial_capital, fitness_metric = task_data
    logger.debug(f"[Worker] Starting sync backtest for Sol {solution_idx}, Mint {mint}") # Log entry
    result = None
    fitness = None
    try:
        # asyncio.run executes the async function in a new event loop
        # Important: Ensure run_backtest is async
        # Log before the potentially blocking call
        logger.debug(f"[Worker] Calling asyncio.run(run_backtest(...)) for Sol {solution_idx}, Mint {mint}")
        result = asyncio.run(run_backtest(parameters, df_data, initial_capital))
        # Log after the call completes
        logger.debug(f"[Worker] asyncio.run(run_backtest(...)) completed for Sol {solution_idx}, Mint {mint}")

        if isinstance(result, dict):
            fitness = result.get(fitness_metric)
            if fitness is not None and pd.notna(fitness):
                logger.debug(f"[Worker] Finished sync backtest for Sol {solution_idx}, Mint {mint}. Fitness: {fitness:.4f}")
                return solution_idx, mint, fitness
            else:
                logger.warning(f"Invalid fitness metric '{fitness_metric}' in result for Sol {solution_idx}, Mint {mint}. Result: {result}")
                return solution_idx, mint, None # Indicate invalid fitness
        else:
             logger.warning(f"Unexpected result type {type(result)} for Sol {solution_idx}, Mint {mint}.")
             return solution_idx, mint, None # Indicate failure
    except Exception as e:
        # Log the full traceback from the worker process
        logger.error(f"[Worker] Exception in run_backtest_sync for Sol {solution_idx}, Mint {mint}: {e}")
        # Log traceback explicitly
        logger.error(f"[Worker] Traceback:\n{traceback.format_exc()}")
        # Return failure indicator
        return solution_idx, mint, None


def calculate_average_fitness(results):
    """Calculates average fitness from multiprocessing results."""
    aggregated_fitness = {} # {sol_idx: {'total': 0.0, 'count': 0}}

    for result_tuple in results:
        if result_tuple is None: continue # Skip tasks that failed completely
        sol_idx, mint, fitness = result_tuple
        if fitness is not None: # Check if fitness was valid
            if sol_idx not in aggregated_fitness:
                aggregated_fitness[sol_idx] = {'total': 0.0, 'count': 0}
            aggregated_fitness[sol_idx]['total'] += fitness
            aggregated_fitness[sol_idx]['count'] += 1
        # else: logger.warning(f"Received None fitness for Sol {sol_idx}, Mint {mint}")

    avg_fitness_list = []
    num_solutions = max(aggregated_fitness.keys()) + 1 if aggregated_fitness else 0

    for sol_idx in range(num_solutions): # Iterate up to the max index encountered
        if (sol_idx in aggregated_fitness and 
            aggregated_fitness[sol_idx]['count'] > 0):
            total = aggregated_fitness[sol_idx]['total']
            count = aggregated_fitness[sol_idx]['count']
            avg_fitness = total / count
            # logger.debug(f"Sol {sol_idx}: Avg Fitness={avg_fitness:.4f} ({count} tokens)")
        else:
            # logger.warning(f"No valid backtests for Sol {sol_idx}. Assigning worst fitness.")
            avg_fitness = -float('inf') if FITNESS_GOAL == 'max' else float('inf')
        avg_fitness_list.append(avg_fitness)

    return avg_fitness_list


def fitness_func_mp(ga_instance, solution, sol_idx):
    """
    PyGAD fitness function using multiprocessing pool for backtests.
    Uses the 'train' dataset globally.
    """
    logger.debug(f"Evaluating solution {sol_idx}: {solution}")
    global historical_data_sets, pool # Access global data and pool

    start_time = time.time()
    worst_fitness = -float('inf') if FITNESS_GOAL == 'max' else float('inf')
    fitness = worst_fitness # Default to worst

    data_for_backtest = historical_data_sets.get('train', {})
    if not data_for_backtest:
        logger.error("Training data not found globally for fitness calculation.")
        return worst_fitness

    parameters = {param['name']: solution[i] for i, param in enumerate(OPTIMIZABLE_PARAMETERS)}

    # Prepare tasks for the current solution across all training tokens
    tasks = []
    for mint, df_data in data_for_backtest.items():
        if not df_data.empty:
            # Pass solution index, params, mint, data, capital, metric name
            tasks.append((sol_idx, parameters.copy(), mint, df_data.copy(), BACKTEST_INITIAL_CAPITAL, FITNESS_METRIC))
            # logger.debug(f"Created task: {tasks[-1]}") 

    if not tasks:
        logger.warning(f"No backtest tasks generated for solution {sol_idx}.")
        return worst_fitness

    try:
        # Map tasks to the pool
        # logger.debug(f"Submitting {len(tasks)} backtest tasks for solution {sol_idx} to pool.")
        results = pool.map(run_backtest_sync, tasks)

        # Aggregate results for this specific solution
        valid_fitness_values = [res[2] for res in results if res is not None and res[2] is not None]

        if valid_fitness_values:
            fitness = sum(valid_fitness_values) / len(valid_fitness_values)
        else:
            logger.warning(f"No valid fitness values obtained for solution {sol_idx}.")
            fitness = worst_fitness

    except Exception as e:
        logger.exception(f"Error during multiprocessing fitness calculation for solution {sol_idx}: {e}")
        logger.error(traceback.format_exc())  # Add traceback logging
        fitness = worst_fitness

    end_time = time.time()
    # logger.debug(f"Sol {sol_idx} Fitness: {fitness:.4f}, Time: {end_time - start_time:.2f}s") # Log fitness + time

    # Handle NaN/inf before returning
    if pd.isna(fitness) or fitness == -float('inf') or fitness == float('inf'):
        return -1e10 # Return a very small number for maximization if fitness is invalid

    return fitness

def run_backtest_for_fitness(solutions, data_set_key='train'):
    # ... existing code ...
    data_for_backtest = historical_data_sets.get(data_set_key, {})
    if not data_for_backtest:
        logger.warning(f"No data found for {data_set_key}. Returning worst fitness.")
        return [-float('inf') if FITNESS_GOAL == 'max' else float('inf')] * len(solutions)

    for sol_idx, solution in enumerate(solutions):
        logger.debug(f"Processing solution {sol_idx} for {data_set_key}") # Added
        parameters = {param['name']: solution[i] for i, param in enumerate(OPTIMIZABLE_PARAMETERS)}
        tasks = []
        for mint, df_data in data_for_backtest.items():
            logger.debug(f"Running backtest for mint {mint} in {data_set_key}") # Added
            if df_data.empty:
                logger.warning(f"Dataframe is empty for mint {mint} in {data_set_key}") # Added
                continue
            try:
                tasks.append((sol_idx, parameters.copy(), mint, df_data.copy(), BACKTEST_INITIAL_CAPITAL, FITNESS_METRIC))
                #logger.debug(f"Created task: {tasks[-1]}")  # Log the last added task
            except Exception as e:
                logger.exception(f"Error creating task for mint {mint} in {data_set_key}: {e}") # Added

# --- Main Execution ---
async def main():
    global db_client, historical_data_sets, pool # Declare usage of globals
    # setup_logging()

    # --- Database Connection ---
    db_client = DatabaseClient()
    try:
        await db_client.connect()
    except Exception as e:
        logger.critical(f"Failed to connect to database: {e}")
        return

    # --- Load Data using the outsourced function ---
    # Get dates and split config from ga_config
    start_date = HISTORICAL_DATA_START_TS
    end_date = HISTORICAL_DATA_END_TS
    data_split_config = DATA_SPLIT

    logger.info("Loading and splitting data using function from utils...")
    loaded_data = await load_and_split_data(db_client, start_date, end_date, data_split_config)

    if loaded_data is None:
        logger.critical("Failed to load or split data via utils function. Exiting.")
        await db_client.close()
        return

    # Assign to global variable (if fitness function relies on it)
    # Alternatively, pass 'loaded_data' to the fitness function if possible with PyGAD setup
    historical_data_sets = loaded_data

    logger.info(f"Training set size: {len(historical_data_sets.get('train', {}))}")
    logger.info(f"Validation set size: {len(historical_data_sets.get('validation', {}))}")
    logger.info(f"Test set size: {len(historical_data_sets.get('test', {}))}")

    if not historical_data_sets.get('train'):
        logger.critical("No training data loaded. Cannot run GA. Exiting.")
        await db_client.close()
        return
    logger.info("Data loaded and split successfully.")

    logger.info(f"Keys in hist_data_dict: {list(historical_data_sets.keys())}")  # Corrected variable name
    # for mint, df in historical_data_sets.items(): # Corrected variable name
    #     logger.info(f"Data for mint {mint}:")
        #logger.info(df.head().to_string())  # Print first few rows as string

    # --- PyGAD Configuration ---
    gene_space = []
    gene_type = []
    init_range_low = []
    init_range_high = []

    for param in OPTIMIZABLE_PARAMETERS:
        # Determine if using 'values' (discrete) or 'low'/'high' (continuous)
        if 'values' in param:
            gene_space.append(param['values'])
            # For discrete spaces, init_range might not be directly applicable in PyGAD
            # PyGAD typically samples from the 'values' list for initialization.
            # Add placeholder bounds, though they might not be used for discrete init.
            init_range_low.append(min(param['values']))
            init_range_high.append(max(param['values']))
        elif 'low' in param and 'high' in param:
            gene_space.append({'low': param['low'], 'high': param['high']})
            init_range_low.append(param['low'])
            init_range_high.append(param['high'])
        else:
             logger.error(f"Invalid configuration for parameter {param['name']}. Missing 'values' or 'low'/'high'.")
             await db_client.close()
             return
        
        gene_type.append(param['type']) # Ensure types are correctly specified (float/int)

    # (Temporary - for testing)
    # for param in OPTIMIZABLE_PARAMETERS:
    #     if 'type' in param:
    #         del param['type']

    import copy
    optimizable_params_serializable = copy.deepcopy(OPTIMIZABLE_PARAMETERS)
    for param in optimizable_params_serializable:
        if 'type' in param:
            param['type'] = str(param['type'])  # Convert type to string

    logger.debug(f"OPTIMIZABLE_PARAMETERS (serializable): {json.dumps(optimizable_params_serializable, indent=4)}")

    # Define callback for generation completion
    def on_generation(ga_instance):
        generation = ga_instance.generations_completed
        # Access fitness securely
        if ga_instance.last_generation_fitness is not None and len(ga_instance.last_generation_fitness) > 0:
             best_fitness_idx = ga_instance.best_solution(pop_fitness=ga_instance.last_generation_fitness)[2]
             best_fitness = ga_instance.last_generation_fitness[best_fitness_idx]
             logger.info(f"Generation {generation} finished. Best Fitness: {best_fitness:.4f}")

             # Log best solution periodically
             if generation % 10 == 0:
                 solution, _, _ = ga_instance.best_solution(pop_fitness=ga_instance.last_generation_fitness)
                 best_params_so_far = {param['name']: solution[i] for i, param in enumerate(OPTIMIZABLE_PARAMETERS)}
                 logger.info(f"Best solution @ Gen {generation}: Fitness={best_fitness:.4f}, Params={json.dumps(best_params_so_far)}")
        else:
             logger.warning(f"Generation {generation} finished. Fitness data not available yet.")

    def on_initialization(ga_instance):
        logger.info("Initial population created. Inspecting...")
        for i in range(min(5, ga_instance.sol_per_pop)):  # Check first 5
            solution = ga_instance.population[i]
            fitness = fitness_func_mp(ga_instance, solution, i)
            logger.info(f"Initial Sol {i}: {solution}, Fitness={fitness}")

    logger.info(f"Setting up PyGAD: Pop={POPULATION_SIZE}, Gens={NUM_GENERATIONS}, Genes={len(OPTIMIZABLE_PARAMETERS)}")
    ga_instance = pygad.GA(
        num_generations=NUM_GENERATIONS,
        num_parents_mating=int(POPULATION_SIZE * 0.25),
        # Use the multiprocessing fitness function
        fitness_func=fitness_func_mp,
        sol_per_pop=POPULATION_SIZE,
        num_genes=len(OPTIMIZABLE_PARAMETERS),
        gene_space=gene_space,
        gene_type=gene_type,
        # Provide initial ranges for mutation if needed, esp. for continuous
        init_range_low=init_range_low,
        init_range_high=init_range_high,
        parent_selection_type="sss",
        crossover_type="single_point",
        crossover_probability=CROSSOVER_PROBABILITY,
        mutation_type="random", # Consider adaptive mutation later if needed
        mutation_probability=MUTATION_PROBABILITY,
        # Adjust mutation range for continuous/integer types if using random mutation
        mutation_num_genes=max(1, int(len(OPTIMIZABLE_PARAMETERS) * 0.1)), # Mutate ~10% of genes
        keep_elitism=2,
        on_generation=on_generation,
        on_start=on_initialization,
        parallel_processing=None # Disable PyGAD internal parallel processing as we use multiprocessing Pool
        # stop_criteria=["saturate_10"] # Example
    )

    # --- Run GA ---
    logger.info("Starting Genetic Algorithm optimization...")
    start_ga_time = time.time()
    try:
        ga_instance.run()
    except Exception as ga_err:
        logger.exception(f"Error during GA execution: {ga_err}")
    # Pool closure is handled outside main() in the `if __name__ == '__main__':` block now

    end_ga_time = time.time()
    logger.info(f"GA optimization finished or stopped after {end_ga_time - start_ga_time:.2f} seconds.")

    # --- Results ---
    if hasattr(ga_instance, 'best_solution_generation') and ga_instance.best_solution_generation != -1:
        solution, solution_fitness, _ = ga_instance.best_solution()
        logger.info(f"Best solution found (Fitness = {solution_fitness}):")
        best_params = {param['name']: solution[i] for i, param in enumerate(OPTIMIZABLE_PARAMETERS)}
        logger.info(json.dumps(best_params, indent=4))

        # --- Run Validation and Testing Sequentially using Async Helper ---
        validation_fitness = test_fitness = -float('inf') if FITNESS_GOAL == 'max' else float('inf')
        all_metrics_validation = {}
        all_metrics_test = {}

        logger.info("Running validation on the best solution...")
        if historical_data_sets.get('validation'):
            val_results = run_backtest_for_fitness([solution], data_set_key='validation')
            if val_results: validation_fitness = val_results[0]
            # Run full backtest again to get all metrics (optional)
            # all_metrics_validation = await run_backtest(best_params, combined_validation_df, BACKTEST_INITIAL_CAPITAL)

        logger.info("Running final test on the best solution...")
        if historical_data_sets.get('test'):
            test_results = run_backtest_for_fitness([solution], data_set_key='test')
            if test_results: test_fitness = test_results[0]
            # Run full backtest again to get all metrics (optional)
            # all_metrics_test = await run_backtest(best_params, combined_test_df, BACKTEST_INITIAL_CAPITAL)

        logger.info(f"Final Evaluation: Train Fitness={solution_fitness:.4f}, Validation Fitness={validation_fitness:.4f}, Test Fitness={test_fitness:.4f}")

        # --- Save Results ---
        # ... (saving logic remains largely the same, using the final fitness values) ...
        results_filename = f"ga_results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        results_data = {
            'best_solution_parameters': best_params,
            'best_solution_fitness_training': solution_fitness,
            'validation_fitness': validation_fitness,
            'test_fitness': test_fitness,
            # Include detailed metrics if calculated
            # 'validation_metrics': all_metrics_validation,
            # 'test_metrics': all_metrics_test,
            'ga_config': { # Store config used for this run
                'population_size': POPULATION_SIZE,
                'num_generations': NUM_GENERATIONS,
                'crossover_probability': CROSSOVER_PROBABILITY,
                'mutation_probability': MUTATION_PROBABILITY,
                'fitness_metric': FITNESS_METRIC,
                'fitness_goal': FITNESS_GOAL,
                'data_split': DATA_SPLIT,
                'backtest_initial_capital': BACKTEST_INITIAL_CAPITAL,
                'data_start_date': HISTORICAL_DATA_START_TS.isoformat(),
                'data_end_date': HISTORICAL_DATA_END_TS.isoformat()
             },
            'optimizable_parameters_config': OPTIMIZABLE_PARAMETERS
        }
        # Save logic... (ensure numpy/datetime conversion)
        def convert_types(obj):
              if isinstance(obj, np.integer): return int(obj)
              elif isinstance(obj, np.floating): return float(obj)
              elif isinstance(obj, np.ndarray): return obj.tolist()
              elif isinstance(obj, (datetime, pd.Timestamp)): return obj.isoformat()
              elif obj == float('inf'): return 'Infinity'
              elif obj == float('-inf'): return '-Infinity'
              return obj
        try:
            with open(results_filename, 'w') as f:
                json.dump(results_data, f, indent=4, default=convert_types)
            logger.info(f"Saved GA results to {results_filename}")
        except Exception as e:
             logger.error(f"Failed to save results to JSON: {e}")


        # --- Plotting ---
        try:
             plot_save_path = os.path.join(os.getcwd(), f"ga_fitness_plot_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png")
             ga_instance.plot_fitness(save_dir=plot_save_path)
             logger.info(f"Saved fitness plot to {plot_save_path}")
        except Exception as plot_err:
             logger.error(f"Failed to save fitness plot: {plot_err}")


    else:
         logger.error("GA did not complete successfully or find a valid solution.")

    # --- Cleanup ---
    await db_client.close()
    logger.info("Optimizer finished.")

# --- !! IMPORTANT GUARD !! ---
if __name__ == "__main__":
    setup_logging()
    # Add freeze_support() here
    freeze_support()

    # Initialize the pool here, only in the main process
    num_processes = max(1, cpu_count() - 2)
    # You can temporarily set num_processes = 1 here for debugging
    #num_processes = 1
    logger.info(f"[Main] DEBUG: Running with {num_processes} processes.")
    pool = Pool(processes=num_processes) # Assign to global pool variable
    logger.info(f"Initialized Multiprocessing Pool with {num_processes} processes.")

    try:
        # Run the main async function
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Keyboard interrupt received. Shutting down...")
    except Exception as e:
         logger.critical(f"Critical error in main execution: {e}", exc_info=True)
    finally:
        # Ensure the pool is closed gracefully
        if pool:
            logger.info("Closing multiprocessing pool...")
            pool.close()
            pool.join()
            logger.info("Multiprocessing pool closed.")
