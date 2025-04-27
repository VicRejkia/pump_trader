# FILE: ga_optimizer.py (Modified for Sampling & Lifespan)

"""
Genetic Algorithm (GA) based Optimizer for Tuning Trading Bot Parameters.

This script uses the PyGAD library to evolve a population of trading parameter sets
by evaluating their performance on historical data using the backtester module.
It leverages multiprocessing for parallel fitness evaluation and implements token
subset sampling for faster fitness calculation.
"""

import os
import asyncio
import pygad
import numpy as np
import pandas as pd
from datetime import datetime, timezone
import time
import json
import random # For sampling
from multiprocessing import Pool, cpu_count, freeze_support, Manager
from typing import List, Dict, Any, Tuple, Optional, Union
import traceback
import copy

# --- Project Modules ---
from logger import logger, setup_logging
from ga_config import (
    OPTIMIZABLE_PARAMETERS, POPULATION_SIZE, NUM_GENERATIONS,
    CROSSOVER_PROBABILITY, MUTATION_PROBABILITY, FITNESS_METRIC, FITNESS_GOAL,
    DATA_SPLIT, BACKTEST_INITIAL_CAPITAL, RESULTS_DIR,
    HISTORICAL_DATA_START_TS, HISTORICAL_DATA_END_TS, MULTIPROCESSING_CORES,
    KEEP_ELITISM, PARENT_SELECTION_TYPE, CROSSOVER_TYPE, MUTATION_TYPE,
    GA_FITNESS_SAMPLE_SIZE # Import the sample size config
)
from database_handler import DatabaseClient # Keep DatabaseClient for potential future use if needed directly
from backtester import run_backtest, calculate_performance_metrics
# Use the improved data loading utility
from utils import load_and_split_data, NpEncoder

# --- Global Variables ---
manager = None
historical_data_sets_shared = None
# Store token lifespans (start_ts, end_ts) fetched once
token_lifespans_shared = None
pool_ref: Optional[Pool] = None


# --- Fitness Function Worker ---

def run_backtest_sync_worker(task_data: Tuple[int, Dict[str, Any], str, pd.DataFrame, Optional[datetime], float, str]) -> Optional[Tuple[int, str, float]]:
    """
    Synchronous wrapper for run_backtest suitable for multiprocessing pool workers.
    Includes handling for token max_timestamp (lifespan end).

    Args:
        task_data: A tuple containing:
            - solution_idx (int): Index of the solution in the population.
            - parameters (dict): The parameter set for this solution.
            - mint (str): The mint address of the token to backtest.
            - df_data (pd.DataFrame): Historical data for the mint.
            - max_timestamp (Optional[datetime]): The timestamp when the token died, or None.
            - initial_capital (float): Starting capital for the backtest.
            - fitness_metric (str): The metric to extract from results.

    Returns:
        A tuple (solution_idx, mint, fitness_value) on success,
        or None if the backtest fails or the metric is invalid.
    """
    solution_idx, parameters, mint, df_data, max_timestamp, initial_capital, fitness_metric = task_data
    # logger.debug(f"[Worker {os.getpid()}] Starting sync backtest for Sol {solution_idx}, Mint {mint}, End: {max_timestamp}") # Optional detailed log

    # Ensure DataFrame index is DatetimeIndex for resampling in backtester
    if not isinstance(df_data.index, pd.DatetimeIndex):
        try:
            df_data.index = pd.to_datetime(df_data.index, utc=True)
        except Exception as e:
            logger.error(f"[Worker {os.getpid()}] Failed to convert index to DatetimeIndex for Mint {mint}: {e}")
            return None

    if df_data.empty:
        logger.warning(f"[Worker {os.getpid()}] Empty DataFrame received for Mint {mint}. Skipping backtest.")
        return None

    result: Optional[Dict[str, Any]] = None
    fitness: Optional[float] = None

    try:
        # Execute the asynchronous backtest function with max_timestamp
        result = asyncio.run(run_backtest(parameters, df_data, initial_capital, max_timestamp)) # Pass max_timestamp

        if isinstance(result, dict):
            fitness = result.get(fitness_metric)
            if fitness is not None and pd.notna(fitness) and np.isfinite(fitness):
                # logger.debug(f"[Worker {os.getpid()}] Finished backtest Sol {solution_idx}, Mint {mint}. Fitness ({fitness_metric}): {fitness:.4f}")
                return solution_idx, mint, float(fitness)
            else:
                logger.warning(f"[Worker {os.getpid()}] Invalid/non-finite fitness metric '{fitness_metric}' for Sol {solution_idx}, Mint {mint}. Result: {result}, Fitness: {fitness}")
                return None # Indicate invalid fitness
        else:
             logger.warning(f"[Worker {os.getpid()}] Unexpected result type {type(result)} for Sol {solution_idx}, Mint {mint}.")
             return None # Indicate failure

    except ValueError as ve: # Catch specific errors like empty data in backtester
         logger.error(f"[Worker {os.getpid()}] ValueError in backtest for Sol {solution_idx}, Mint {mint}: {ve}")
         return None
    except Exception as e:
        logger.error(f"[Worker {os.getpid()}] Exception in run_backtest_sync for Sol {solution_idx}, Mint {mint}: {e.__class__.__name__}")
        # logger.exception(f"[Worker {os.getpid()}] Full traceback for Sol {solution_idx}, Mint {mint}:") # Optional full traceback log
        return None # Return failure indicator

# --- Fitness Function (Main Process) ---

def fitness_func_main_process(ga_instance, solution: np.ndarray, solution_idx: int) -> float:
    """
    PyGAD fitness function executed in the main process.
    Prepares tasks for the multiprocessing pool using a *sample* of training tokens
    and aggregates results.

    Args:
        ga_instance: The pygad.GA instance.
        solution: The numpy array representing the parameter set (genes).
        solution_idx: The index of the solution in the current population.

    Returns:
        The calculated average fitness for the solution over the sampled tokens,
        or a penalty value if errors occur.
    """
    global pool_ref, historical_data_sets_shared, token_lifespans_shared
    if pool_ref is None:
        logger.critical("Multiprocessing pool (pool_ref) is None! Cannot run fitness.")
        return -float('inf') if FITNESS_GOAL == 'max' else float('inf')
    if historical_data_sets_shared is None or token_lifespans_shared is None:
        logger.critical("Shared historical data or token lifespans are None!")
        return -float('inf') if FITNESS_GOAL == 'max' else float('inf')

    worst_fitness = -float('inf') if FITNESS_GOAL == 'max' else float('inf')
    data_for_backtest = dict(historical_data_sets_shared.get('train', {}))
    token_lifespans = dict(token_lifespans_shared) # Get lifespan info

    if not data_for_backtest:
        logger.error("[Main] Training data not found in shared dict for fitness calculation.")
        return worst_fitness

    # Convert solution to parameter dictionary
    parameters = {}
    for i, param_config in enumerate(OPTIMIZABLE_PARAMETERS):
        param_type = param_config['type']
        # Ensure correct type casting (rounding for int)
        parameters[param_config['name']] = param_type(np.round(solution[i])) if param_type == int else param_type(solution[i])

    # --- Token Sampling ---
    available_mints = list(data_for_backtest.keys())
    mints_to_evaluate = []
    if GA_FITNESS_SAMPLE_SIZE is None or GA_FITNESS_SAMPLE_SIZE <= 0 or GA_FITNESS_SAMPLE_SIZE >= len(available_mints):
        # Use all available tokens if sampling is disabled or sample size is too large
        mints_to_evaluate = available_mints
        # logger.debug(f"Sol {solution_idx}: Evaluating on all {len(available_mints)} training tokens.")
    else:
        # Randomly sample tokens without replacement
        if len(available_mints) > GA_FITNESS_SAMPLE_SIZE:
            mints_to_evaluate = random.sample(available_mints, GA_FITNESS_SAMPLE_SIZE)
            # logger.debug(f"Sol {solution_idx}: Evaluating on {GA_FITNESS_SAMPLE_SIZE} sampled tokens.")
        else:
             mints_to_evaluate = available_mints # Sample size larger than available, use all
             # logger.debug(f"Sol {solution_idx}: Sample size >= available tokens, evaluating on all {len(available_mints)}.")

    # Prepare tasks for the sampled tokens (same as before)
    tasks = []
    for mint in mints_to_evaluate:
        df_data = data_for_backtest.get(mint)
        lifespan = token_lifespans.get(mint)
        max_timestamp = lifespan['end_ts'] if lifespan else None

        if isinstance(df_data, pd.DataFrame) and not df_data.empty and isinstance(df_data.index, pd.DatetimeIndex):
            # Task items are the tuples that run_backtest_sync_worker expects as its single argument
            tasks.append((solution_idx, parameters.copy(), mint, df_data, max_timestamp, BACKTEST_INITIAL_CAPITAL, FITNESS_METRIC))
        else:
            logger.warning(f"[Main] Invalid data for sampled mint {mint}. Skipping.")

    if not tasks:
        logger.warning(f"[Main] No valid backtest tasks generated for solution {solution_idx} after sampling.")
        return worst_fitness

    aggregated_fitness: float = 0.0
    valid_results_count: int = 0

    try:
        # ***** CHANGE STARMAP TO MAP *****
        # pool.map applies the worker function to each item (tuple) in the tasks list
        results: List[Optional[Tuple[int, str, float]]] = pool_ref.map(run_backtest_sync_worker, tasks)
        # ***** END CHANGE *****

        # Aggregate results (same as before)
        for result_tuple in results:
            if result_tuple is not None:
                # Check if the result corresponds to the current solution index
                # This check might be redundant with pool.map if order is preserved, but safe
                res_sol_idx, _, fitness_value = result_tuple
                if res_sol_idx == solution_idx:
                     aggregated_fitness += fitness_value
                     valid_results_count += 1
                # else: # Log if results seem out of order (shouldn't happen with map)
                #    logger.warning(f"Received result for solution {res_sol_idx} while processing {solution_idx}")

        if valid_results_count > 0:
            average_fitness = aggregated_fitness / valid_results_count
            # logger.debug(f"[Main] Sol {solution_idx}: Avg Fitness ({valid_results_count} tokens) = {average_fitness:.6f}")
        else:
            logger.warning(f"[Main] No valid backtest results for solution {solution_idx} (sampled {len(tasks)}).")
            average_fitness = worst_fitness

    except Exception as e:
        # Log the specific exception type and message
        logger.error(f"[Main] Error during pool fitness calculation for solution {solution_idx} ({type(e).__name__}): {e}")
        # Include traceback for detailed debugging if needed
        # import traceback
        # logger.error(traceback.format_exc())
        average_fitness = worst_fitness # Assign penalty on error

    # Final check for NaN/inf fitness before returning (same as before)
    if pd.isna(average_fitness) or not np.isfinite(average_fitness):
        logger.warning(f"[Main] Fitness for Sol {solution_idx} is NaN/Inf ({average_fitness}). Returning penalty.")
        return -1e10 if FITNESS_GOAL == 'max' else 1e10

    return average_fitness

# --- PyGAD Callbacks ---

def on_generation(ga_instance):
    """Callback function executed after each generation."""
    generation = ga_instance.generations_completed
    if ga_instance.last_generation_fitness is None or len(ga_instance.last_generation_fitness) == 0:
        logger.warning(f"--- Generation {generation} Finished --- Fitness values not yet available.")
        return

    try:
        best_solution, best_fitness, _ = ga_instance.best_solution(ga_instance.last_generation_fitness)
        avg_fitness = np.mean(ga_instance.last_generation_fitness)
        logger.info(f"--- Generation {generation} Finished --- Best Fitness: {best_fitness:.6f} | Avg Fitness: {avg_fitness:.6f}")

        # Log best parameters periodically
        if generation % 5 == 0 or generation == ga_instance.num_generations:
            best_params_dict = {}
            for i, param_config in enumerate(OPTIMIZABLE_PARAMETERS):
                param_type = param_config['type']
                best_params_dict[param_config['name']] = param_type(np.round(best_solution[i])) if param_type == int else param_type(best_solution[i])
            logger.info(f"Best Solution Parameters @ Gen {generation}:\n{json.dumps(best_params_dict, indent=2)}")
    except Exception as e:
        logger.error(f"Error in on_generation callback: {e}", exc_info=True)


# --- Helper to Run Backtests on Final Solution ---

async def evaluate_solution(
    parameters: Dict[str, Any],
    data_set_key: str,
    historical_data: Dict[str, pd.DataFrame], # Use regular dict here
    token_lifespans: Dict[str, Dict[str, datetime]], # Pass lifespan info
    initial_capital: float
) -> Dict[str, Any]:
    """
    Runs backtests for a given parameter set on all tokens in a specified data set,
    respecting token lifespans.

    Args:
        parameters: The parameter set to evaluate.
        data_set_key: 'validation' or 'test'.
        historical_data: Dictionary containing the dataframes for the specified set.
        token_lifespans: Dictionary mapping mints to their {'start_ts', 'end_ts'}.
        initial_capital: Starting capital.

    Returns:
        Dictionary containing aggregated performance metrics.
    """
    logger.info(f"--- Evaluating Solution on '{data_set_key}' Set ---")
    data_to_use = historical_data.get(data_set_key, {})
    if not data_to_use:
        logger.warning(f"No data for '{data_set_key}' set.")
        return {"error": f"No data in {data_set_key} set"}

    tasks = []
    for mint, df_data in data_to_use.items():
        if isinstance(df_data, pd.DataFrame) and not df_data.empty and isinstance(df_data.index, pd.DatetimeIndex):
            # Ensure index is datetime before passing
            if not isinstance(df_data.index, pd.DatetimeIndex):
                 try:
                     df_data.index = pd.to_datetime(df_data.index, utc=True)
                 except Exception as e:
                     logger.error(f"Failed to convert index for eval mint {mint}: {e}. Skipping.")
                     continue

            # Get max_timestamp for this token
            lifespan = token_lifespans.get(mint)
            max_timestamp = lifespan['end_ts'] if lifespan else None

            tasks.append(asyncio.create_task(
                run_backtest(parameters, df_data, initial_capital, max_timestamp), # Pass max_timestamp
                name=f"eval_{mint}"
            ))
        else:
             logger.warning(f"Skipping eval for mint {mint} ('{data_set_key}') due to invalid data.")

    if not tasks:
         logger.warning(f"No valid eval tasks created for '{data_set_key}' set.")
         return {"error": f"No valid tasks for {data_set_key} set"}

    # Execute tasks and gather results
    results_raw = await asyncio.gather(*tasks, return_exceptions=True)

    # --- Aggregate Results ---
    successful_results = []
    total_pnl_agg, total_trades_agg, total_wins_agg, final_portfolio_value_agg = 0.0, 0, 0, 0.0
    initial_capital_sum = 0.0 # Sum initial capital across runs for avg calc base

    for i, res in enumerate(results_raw):
        mint_name = tasks[i].get_name().split('_')[-1] # Extract mint from task name
        if isinstance(res, dict):
            # Validate essential metrics
            pnl = res.get('total_pnl')
            final_val = res.get('final_portfolio_value')
            num_trades = res.get('total_trades', 0)
            init_cap = res.get('initial_capital', initial_capital)

            if pnl is not None and final_val is not None and pd.notna(pnl) and pd.notna(final_val):
                successful_results.append(res)
                total_pnl_agg += pnl
                total_trades_agg += num_trades
                total_wins_agg += res.get('winning_trades', 0)
                final_portfolio_value_agg += final_val
                initial_capital_sum += init_cap
                logger.debug(f"Eval success ({data_set_key}, {mint_name}): PnL={pnl:.4f}, FinalVal={final_val:.4f}, Trades={num_trades}")
            else:
                logger.warning(f"Eval backtest for {mint_name} ('{data_set_key}') produced invalid result (NaN/missing): {res}")
        elif isinstance(res, Exception):
            logger.error(f"Eval backtest task for {mint_name} ('{data_set_key}') failed: {res}", exc_info=False) # Keep log concise
        else:
            logger.warning(f"Unexpected eval result type for {mint_name} ('{data_set_key}'): {type(res)}")

    # --- Calculate Aggregated Metrics ---
    num_valid_backtests = len(successful_results)
    if num_valid_backtests == 0:
        logger.error(f"All eval backtests failed for '{data_set_key}' set.")
        return {"error": f"All backtests failed for {data_set_key} set"}

    avg_final_value = final_portfolio_value_agg / num_valid_backtests
    avg_pnl = total_pnl_agg / num_valid_backtests
    overall_win_rate = (total_wins_agg / total_trades_agg * 100) if total_trades_agg > 0 else 0.0
    # Calculate average return percentage based on initial capital
    avg_return_percent = (avg_pnl / (initial_capital_sum / num_valid_backtests) * 100) if initial_capital_sum > 0 else 0.0
    avg_max_drawdown = sum(r.get('max_drawdown', 0.0) for r in successful_results) / num_valid_backtests
    # Determine the primary fitness metric value for this evaluation set
    if FITNESS_METRIC == "final_portfolio_value":
        fitness_metric_value_eval = avg_final_value
    elif FITNESS_METRIC == "total_pnl":
        fitness_metric_value_eval = avg_pnl
    # Add other FITNESS_METRIC options here if needed
    else:
         fitness_metric_value_eval = avg_final_value # Default to final value

    aggregated_metrics = {
        "data_set": data_set_key,
        "num_tokens_evaluated": num_valid_backtests,
        f"average_{FITNESS_METRIC}": fitness_metric_value_eval,
        "average_final_portfolio_value": avg_final_value,
        "average_total_pnl": avg_pnl,
        "average_return_percent": avg_return_percent, # Added average return %
        "overall_win_rate_percent": overall_win_rate,
        "average_max_drawdown_percent": avg_max_drawdown,
        "total_trades_executed": total_trades_agg # Renamed for clarity
    }
    logger.info(f"--- Evaluation Metrics ({data_set_key}) ---")
    for k, v in aggregated_metrics.items():
        logger.info(f"  {k}: {v:.4f}" if isinstance(v, float) else f"  {k}: {v}")
    logger.info("-------------------------------------")
    return aggregated_metrics


# --- Main Execution Logic (Async) ---

async def main_async_logic():
    """Main asynchronous function to set up and run the GA optimization."""
    global historical_data_sets_shared, token_lifespans_shared, pool_ref # Access globals
    setup_logging(logger_name="ga_optimizer") # Initialize logging
    db_client = None # Initialize db_client

    # --- Database Connection ---
    try:
        db_client = DatabaseClient()
        await db_client.connect()
        logger.info("[Async Main] Database connected successfully.")
    except Exception as e:
        logger.critical(f"[Async Main] Failed to connect database: {e}")
        return # Exit if DB connection fails

    # --- Load and Prepare Data (using improved function) ---
    start_date = HISTORICAL_DATA_START_TS
    end_date = HISTORICAL_DATA_END_TS
    data_split_config = DATA_SPLIT

    logger.info("Loading and splitting historical data...")
    loaded_results = None
    try:
        # load_and_split_data now returns a tuple: (datasets, lifespans)
        loaded_results = await load_and_split_data(db_client, start_date, end_date, data_split_config)
    except Exception as e:
         logger.error(f"Error occurred during load_and_split_data: {e}", exc_info=True)
         if db_client: await db_client.close()
         logger.info("[Async Main] Database connection closed after data load error.")
         return # Exit if data loading fails

    if loaded_results is None:
        logger.critical("Failed to load or split data. Exiting.")
        if db_client: await db_client.close()
        logger.info("[Async Main] Database connection closed.")
        return

    loaded_data_sets, token_lifespans = loaded_results # Unpack the results
    if not loaded_data_sets or not loaded_data_sets.get('train') or not token_lifespans:
         logger.critical("Training set or token lifespans are empty after loading. Exiting.")
         if db_client: await db_client.close()
         logger.info("[Async Main] Database connection closed.")
         return

    # --- Populate the shared Manager dictionaries ---
    historical_data_sets_shared.update(loaded_data_sets) # Update shared data
    token_lifespans_shared.update(token_lifespans)       # Update shared lifespans
    logger.info("Data and token lifespans loaded into shared dictionary proxies.")
    logger.info(f"Training set size: {len(historical_data_sets_shared.get('train', {}))}")
    logger.info(f"Validation set size: {len(historical_data_sets_shared.get('validation', {}))}")
    logger.info(f"Test set size: {len(historical_data_sets_shared.get('test', {}))}")
    logger.info(f"Lifespan info loaded for {len(token_lifespans_shared)} tokens.")

    # --- PyGAD Configuration ---
    gene_space = []
    init_range_low = []
    init_range_high = []
    gene_type = [] # Keep track of types for casting later if needed

    for param in OPTIMIZABLE_PARAMETERS:
        if 'values' in param:
            # For discrete values, use the list directly
            gene_space.append(param['values'])
            init_range_low.append(min(param['values']))
            init_range_high.append(max(param['values']))
            gene_type.append(param['type'])
        elif 'low' in param and 'high' in param:
            # For continuous range, use the dictionary format PyGAD expects
            gene_space.append({'low': param['low'], 'high': param['high']})
            init_range_low.append(param['low']) # These might not be strictly needed by PyGAD if gene_space is dicts
            init_range_high.append(param['high'])# but are useful for initial population generation logic if default
            gene_type.append(param['type'])
        else:
            logger.error(f"Invalid configuration for parameter {param['name']}. Missing 'values' or 'low'/'high'.")
            if db_client: await db_client.close()
            return
        # No change needed for gene_type list itself, just populate it

    logger.info(f"Setting up PyGAD: Pop={POPULATION_SIZE}, Gens={NUM_GENERATIONS}, Genes={len(OPTIMIZABLE_PARAMETERS)}")
    if pool_ref is None:
        logger.critical("Pool reference (pool_ref) is None before GA initialization.")
        if db_client: await db_client.close() # Close DB before exiting
        return

    # Ensure num_parents_mating is at least 2 and reasonable
    num_parents_mating = max(2, int(POPULATION_SIZE * 0.3)) # Example: 30% parents mate

    ga_instance = pygad.GA(
        num_generations=NUM_GENERATIONS,
        num_parents_mating=num_parents_mating,
        fitness_func=fitness_func_main_process,
        sol_per_pop=POPULATION_SIZE,
        num_genes=len(OPTIMIZABLE_PARAMETERS),
        gene_space=gene_space,          # Provide the defined gene space
        # gene_type=gene_type,          # gene_type is implicitly handled by gene_space if values are correct type
        # init_range_low/high might be redundant if using complex gene_space, but kept for safety
        init_range_low=init_range_low,
        init_range_high=init_range_high,
        parent_selection_type=PARENT_SELECTION_TYPE,
        crossover_type=CROSSOVER_TYPE,
        crossover_probability=CROSSOVER_PROBABILITY,
        mutation_type=MUTATION_TYPE,
        mutation_probability=MUTATION_PROBABILITY,
        mutation_by_replacement=True,   # Consider if this is appropriate
        keep_elitism=max(0, KEEP_ELITISM),
        on_generation=on_generation,
        # stop_criteria=["reach_100.0"] # Example: stop if fitness reaches 100
    )

    # --- Run GA ---
    logger.info("--- Starting Genetic Algorithm Optimization ---")
    start_ga_time = time.time()
    try:
        ga_instance.run() # This is blocking
    except Exception as ga_err:
        logger.exception(f"Error during GA execution: {ga_err}")
    end_ga_time = time.time()
    logger.info(f"--- GA Optimization Finished (Duration: {end_ga_time - start_ga_time:.2f} seconds) ---")

    # --- Results Processing ---
    if hasattr(ga_instance, 'best_solution_generation') and ga_instance.best_solution_generation != -1:
        solution, solution_fitness, _ = ga_instance.best_solution()
        logger.info(f"Best solution found (Training Fitness = {solution_fitness:.6f}):")

        # Decode best solution into parameters dictionary
        best_params = {}
        for i, param_config in enumerate(OPTIMIZABLE_PARAMETERS):
             param_type = param_config['type']
             best_params[param_config['name']] = param_type(np.round(solution[i])) if param_type == int else param_type(solution[i])
        logger.info(f"Best Parameters:\n{json.dumps(best_params, indent=2)}")

        # --- Final Evaluation (using non-shared data and lifespans) ---
        validation_metrics = await evaluate_solution(best_params, 'validation', loaded_data_sets, token_lifespans, BACKTEST_INITIAL_CAPITAL)
        test_metrics = await evaluate_solution(best_params, 'test', loaded_data_sets, token_lifespans, BACKTEST_INITIAL_CAPITAL)

        # --- Save Results ---
        os.makedirs(RESULTS_DIR, exist_ok=True)
        results_filename = os.path.join(RESULTS_DIR, f"ga_results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json")

        # Make optimizable params config serializable
        optimizable_params_serializable = copy.deepcopy(OPTIMIZABLE_PARAMETERS)
        for param in optimizable_params_serializable:
            if 'type' in param: param['type'] = str(param['type']) # Convert type object to string

        results_data = {
            'best_solution_parameters': best_params,
            'best_solution_fitness_training': solution_fitness,
            'validation_metrics': validation_metrics,
            'test_metrics': test_metrics,
            'ga_config': {
                'population_size': POPULATION_SIZE,
                'num_generations': NUM_GENERATIONS,
                'num_parents_mating': num_parents_mating,
                'crossover_probability': CROSSOVER_PROBABILITY,
                'mutation_probability': MUTATION_PROBABILITY,
                'elitism': KEEP_ELITISM,
                'parent_selection': PARENT_SELECTION_TYPE,
                'crossover_type': CROSSOVER_TYPE,
                'mutation_type': MUTATION_TYPE,
                'fitness_metric': FITNESS_METRIC,
                'fitness_goal': FITNESS_GOAL,
                'fitness_sample_size': GA_FITNESS_SAMPLE_SIZE,
                'data_start_date': HISTORICAL_DATA_START_TS.isoformat(),
                'data_end_date': HISTORICAL_DATA_END_TS.isoformat()
            },
            'optimizable_parameters_config': optimizable_params_serializable
        }

        try:
            with open(results_filename, 'w') as f:
                # Use the custom NpEncoder from utils.py
                json.dump(results_data, f, indent=4, cls=NpEncoder)
            logger.info(f"Saved GA results to {results_filename}")
        except Exception as e:
             logger.error(f"Failed to save results to JSON: {e}", exc_info=True)

        # --- Plotting ---
        try:
            if ga_instance.generations_completed > 0 :
                os.makedirs(RESULTS_DIR, exist_ok=True)
                plot_save_path = os.path.join(RESULTS_DIR, f"ga_fitness_plot_{datetime.now().strftime('%Y%m%d_%H%M%S')}")
                # Check if fitness values exist before plotting
                if ga_instance.best_solutions_fitness:
                    ga_instance.plot_fitness(save_dir=plot_save_path)
                    logger.info(f"Saved fitness plot to {plot_save_path}.png")
                else:
                    logger.warning("No fitness data recorded by PyGAD, cannot generate plot.")
            else:
                 logger.warning("GA did not complete any generations, skipping plot.")
        except Exception as plot_err:
             logger.error(f"Failed to save fitness plot: {plot_err}", exc_info=False)
    else:
         logger.error("GA did not complete successfully or find a valid best solution.")

    # --- Cleanup DB Connection ---
    if db_client:
        await db_client.close()
        logger.info("[Async Main] Database connection closed.")
    logger.info("Optimizer async logic finished.")


# --- Entry Point Guard ---
if __name__ == "__main__":
    # Crucial for multiprocessing safety, especially on Windows
    freeze_support()

    manager_context = None
    pool_context = None
    try:
        # Use context managers for cleaner resource handling
        with Manager() as manager:
            historical_data_sets_shared = manager.dict()
            token_lifespans_shared = manager.dict() # Add shared dict for lifespans

            # Determine number of processes
            num_processes = os.cpu_count() - 2 if os.cpu_count() > 2 else 1
            if isinstance(MULTIPROCESSING_CORES, int) and MULTIPROCESSING_CORES >= 1:
                num_processes = MULTIPROCESSING_CORES
            elif isinstance(MULTIPROCESSING_CORES, str) and MULTIPROCESSING_CORES.isdigit():
                 num_processes = int(MULTIPROCESSING_CORES)

            num_processes = max(1, num_processes) # Ensure at least 1 process

            logger.info(f"[Main Entry] Creating Multiprocessing Pool with {num_processes} processes.")
            # Use Pool context manager for automatic cleanup
            with Pool(processes=num_processes) as pool:
                pool_ref = pool # Set global pool reference

                # Run the main asynchronous logic using the created pool
                asyncio.run(main_async_logic())

    except KeyboardInterrupt:
        logger.info("[Main Entry] Keyboard interrupt received. Shutting down...")
    except Exception as e:
         logger.critical(f"[Main Entry] Critical error in GA optimizer entry point: {e}", exc_info=True)
    finally:
        # Pool and Manager cleanup is handled by 'with' statements
        logger.info("[Main Entry] Optimizer finished.")