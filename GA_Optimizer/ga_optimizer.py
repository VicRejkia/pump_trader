# FILE: ga_optimizer.py

"""
Genetic Algorithm (GA) based Optimizer for Tuning Trading Bot Parameters.

This script uses the PyGAD library to evolve a population of trading parameter sets
by evaluating their performance on historical data using the backtester module.
It leverages multiprocessing for parallel fitness evaluation and implements token
subset sampling for faster fitness calculation.
"""

import os
import sys
import asyncio
import pygad
import numpy as np
import pandas as pd
from datetime import datetime, timezone
import time
import json
import random
from multiprocessing import Manager, freeze_support
from typing import List, Dict, Any, Optional, Union

# --- Project Modules ---
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from bot_logger import logger, setup_logging
from GA_Optimizer.ga_config import (
    OPTIMIZABLE_PARAMETERS, POPULATION_SIZE, NUM_GENERATIONS,
    CROSSOVER_PROBABILITY, MUTATION_PROBABILITY, FITNESS_METRIC, FITNESS_GOAL,
    DATA_SPLIT, BACKTEST_INITIAL_CAPITAL, RESULTS_DIR,
    HISTORICAL_DATA_START_TS, HISTORICAL_DATA_END_TS, MULTIPROCESSING_CORES,
    KEEP_ELITISM, PARENT_SELECTION_TYPE, CROSSOVER_TYPE, MUTATION_TYPE,
    GA_FITNESS_SAMPLE_SIZE
)
from database_handler import DatabaseClient
from GA_Optimizer.ga_backtester import run_backtest_sync
from utils import load_and_split_data, NpEncoder


# --- Fitness Function (Executed in Parallel) ---
def fitness_func_main_process(ga_instance, solution: np.ndarray, solution_idx: int) -> float:
    """
    Fitness function called by PyGAD for each solution. It accesses shared
    data attached to the ga_instance object to run the backtest.
    """
    # Define the worst possible fitness score to return in case of errors.
    worst_fitness = -float('inf') if FITNESS_GOAL == 'max' else float('inf')

    # Access the shared data for this worker process.
    data_for_backtest = dict(ga_instance.historical_data_sets_shared.get('train', {}))
    token_lifespans = dict(ga_instance.token_lifespans_shared)
    dexscreener_snapshots = dict(ga_instance.dexscreener_snapshots_shared)
    indicator_cache = ga_instance.indicator_cache

    if not data_for_backtest:
        return worst_fitness

    # Convert the GA's numpy array solution into a human-readable parameter dictionary.
    parameters = {p['name']: p['type'](np.round(solution[i]) if p['type'] == int else solution[i]) for i, p in enumerate(OPTIMIZABLE_PARAMETERS)}

    # If enabled, randomly sample a subset of tokens for faster fitness evaluation.
    available_mints = list(data_for_backtest.keys())
    sample_size = GA_FITNESS_SAMPLE_SIZE
    mints_to_evaluate = available_mints if not sample_size or sample_size <= 0 or sample_size >= len(available_mints) else random.sample(available_mints, min(sample_size, len(available_mints)))

    if not mints_to_evaluate:
        return worst_fitness

    # Run the backtester for each selected token and collect the fitness scores.
    fitness_values = []
    for mint in mints_to_evaluate:
        df_data, lifespan, snapshots = data_for_backtest.get(mint), token_lifespans.get(mint), dexscreener_snapshots.get(mint)
        max_timestamp = lifespan['end_ts'] if lifespan else None
        parameters['mint'] = mint
        try:
            result = run_backtest_sync(parameters, df_data, BACKTEST_INITIAL_CAPITAL, max_timestamp, snapshots, indicator_cache)
            if isinstance(result, dict):
                fitness = result.get(FITNESS_METRIC)
                if fitness is not None and pd.notna(fitness) and np.isfinite(fitness):
                    fitness_values.append(float(fitness))
        except Exception as e:
            logger.error(f"Backtest failed for Sol {solution_idx}, Mint {mint}: {e}", exc_info=False)

    # Return the average fitness across all evaluated tokens.
    if not fitness_values:
        return worst_fitness
    average_fitness = np.mean(fitness_values)
    return average_fitness if np.isfinite(average_fitness) else worst_fitness


# --- PyGAD Callbacks ---
def on_generation(ga_instance):
    """Callback function executed after each generation to log progress."""
    generation = ga_instance.generations_completed
    if not ga_instance.best_solutions:
        logger.warning(f"--- Generation {generation} Finished --- No valid solutions found yet.")
        return
    try:
        # Log the best and average fitness for the completed generation.
        best_fitness = ga_instance.best_solutions_fitness[-1]
        avg_fitness_list = ga_instance.last_generation_fitness
        avg_fitness = np.mean(avg_fitness_list) if avg_fitness_list is not None and len(avg_fitness_list) > 0 else 'N/A'
        avg_fitness_str = f"{avg_fitness:.6f}" if isinstance(avg_fitness, float) else avg_fitness
        logger.info(f"--- Generation {generation} Finished --- Best Fitness: {best_fitness:.6f} | Avg Fitness: {avg_fitness_str}")
        
        # Periodically log the best parameters found so far.
        if generation % 5 == 0 or generation == ga_instance.num_generations:
            best_solution = ga_instance.best_solutions[-1]
            best_params_dict = {p['name']: p['type'](np.round(best_solution[i]) if p['type'] == int else best_solution[i]) for i, p in enumerate(OPTIMIZABLE_PARAMETERS)}
            logger.info(f"Best Solution Parameters @ Gen {generation}:\n{json.dumps(best_params_dict, indent=2)}")
    except Exception as e:
        logger.error(f"Error in on_generation callback: {e}", exc_info=True)


# --- Helper to Run Backtests on Final Solution ---
async def evaluate_solution(parameters: Dict, data_set_key: str, historical_data: Dict, token_lifespans: Dict, dexscreener_snapshots: Dict, initial_capital: float, cache_for_eval: Optional[Dict] = None) -> Dict:
    """Evaluates a final parameter set on a given data set (validation or test)."""
    logger.info(f"--- Evaluating Solution on '{data_set_key}' Set ---")
    data_to_use = historical_data.get(data_set_key, {})
    if not data_to_use: return {"error": f"No data in {data_set_key} set"}
    
    # Sequentially run the backtester for each token in the evaluation set.
    results_raw = []
    for mint, df_data in data_to_use.items():
        if isinstance(df_data, pd.DataFrame) and not df_data.empty:
            lifespan = token_lifespans.get(mint)
            max_timestamp = lifespan['end_ts'] if lifespan else None
            snapshots_for_mint = dexscreener_snapshots.get(mint)
            parameters['mint'] = mint
            try:
                # Direct synchronous call is appropriate here as this function is not parallelized.
                result = run_backtest_sync(parameters, df_data, initial_capital, max_timestamp, snapshots_for_mint, cache_for_eval)
                results_raw.append(result)
            except Exception as e:
                logger.error(f"Error evaluating {mint} on {data_set_key} set: {e}")
                results_raw.append(e) # Append exception to see failure counts

    # Aggregate the results from all tokens in the set.
    successful_results = [res for res in results_raw if isinstance(res, dict) and res.get('total_pnl') is not None]
    if not successful_results: return {"error": f"All backtests failed for {data_set_key} set"}
    
    total_pnl_agg = sum(r['total_pnl'] for r in successful_results)
    avg_pnl = total_pnl_agg / len(successful_results)
    final_portfolio_value_agg = sum(r['final_portfolio_value'] for r in successful_results)
    avg_final_value = final_portfolio_value_agg / len(successful_results)
    total_trades_agg = sum(r.get('total_trades', 0) for r in successful_results)
    total_wins_agg = sum(r.get('winning_trades', 0) for r in successful_results)
    overall_win_rate = (total_wins_agg / total_trades_agg * 100) if total_trades_agg > 0 else 0.0

    return {"data_set": data_set_key, "average_final_portfolio_value": avg_final_value, "average_total_pnl": avg_pnl, "overall_win_rate_percent": overall_win_rate, "total_trades_executed": total_trades_agg}

# --- Main Execution Logic (Async) ---
async def main_async_logic(shared_data_dict, shared_lifespan_dict, shared_snapshot_dict, shared_cache):
    """Main async function to set up and run the GA optimization."""
    setup_logging(logger_name="ga_optimizer")
    db_client = None
    try:
        # Connect to the database and load all historical data.
        db_client = DatabaseClient()
        await db_client.connect()
        logger.info("Loading and splitting historical data...")
        loaded_results = await load_and_split_data(db_client, HISTORICAL_DATA_START_TS, HISTORICAL_DATA_END_TS, DATA_SPLIT)
        if loaded_results is None:
            logger.critical("Failed to load or split data. Exiting."); return
        
        # Unpack data and load it into shared dictionaries for multiprocessing.
        loaded_data_sets, token_lifespans, dexscreener_snapshots = loaded_results
        shared_data_dict.update(loaded_data_sets)
        shared_lifespan_dict.update(token_lifespans)
        shared_snapshot_dict.update(dexscreener_snapshots)
        logger.info("Data loaded into shared dictionaries for multiprocessing.")

        # Prepare the gene space for PyGAD based on the defined optimizable parameters.
        gene_space = [{'low': p['low'], 'high': p['high']} if 'low' in p else p['values'] for p in OPTIMIZABLE_PARAMETERS]
        num_processes = os.cpu_count() - 2 if MULTIPROCESSING_CORES == "auto" and os.cpu_count() and os.cpu_count() > 2 else max(1, int(MULTIPROCESSING_CORES))
        
        # Initialize the PyGAD instance with all GA parameters.
        ga_instance = pygad.GA(num_generations=NUM_GENERATIONS, num_parents_mating=max(2, int(POPULATION_SIZE * 0.3)), fitness_func=fitness_func_main_process, sol_per_pop=POPULATION_SIZE, num_genes=len(OPTIMIZABLE_PARAMETERS), gene_space=gene_space, parent_selection_type=PARENT_SELECTION_TYPE, crossover_type=CROSSOVER_TYPE, crossover_probability=CROSSOVER_PROBABILITY, mutation_type=MUTATION_TYPE, mutation_probability=MUTATION_PROBABILITY, keep_elitism=max(0, KEEP_ELITISM), on_generation=on_generation, parallel_processing=['process', num_processes], stop_criteria="saturate_15")
        
        # Attach the shared data dictionaries to the GA instance so they are accessible in the fitness function.
        ga_instance.historical_data_sets_shared = shared_data_dict
        ga_instance.token_lifespans_shared = shared_lifespan_dict
        ga_instance.dexscreener_snapshots_shared = shared_snapshot_dict
        ga_instance.indicator_cache = shared_cache

        # Start the GA optimization process.
        logger.info(f"--- Starting Genetic Algorithm Optimization ({num_processes} processes) ---")
        start_time = time.time()
        ga_instance.run()
        logger.info(f"--- GA Optimization Finished (Duration: {(time.time() - start_time)/60:.2f} minutes) ---")

        # After the GA finishes, evaluate the best solution on the validation and test sets.
        if hasattr(ga_instance, 'best_solution_generation') and ga_instance.best_solution_generation != -1:
            solution, solution_fitness, _ = ga_instance.best_solution()
            best_params = {p['name']: p['type'](solution[i]) for i, p in enumerate(OPTIMIZABLE_PARAMETERS)}
            logger.info(f"Best solution (Training Fitness = {solution_fitness:.6f}):\n{json.dumps(best_params, indent=2)}")

            eval_cache = dict(shared_cache)
            validation_metrics = await evaluate_solution(best_params, 'validation', loaded_data_sets, token_lifespans, dexscreener_snapshots, BACKTEST_INITIAL_CAPITAL, eval_cache)
            test_metrics = await evaluate_solution(best_params, 'test', loaded_data_sets, token_lifespans, dexscreener_snapshots, BACKTEST_INITIAL_CAPITAL, eval_cache)
            
            # Save the final results and fitness plot to the results directory.
            os.makedirs(RESULTS_DIR, exist_ok=True)
            results_filename = os.path.join(RESULTS_DIR, f"ga_results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json")
            with open(results_filename, 'w') as f:
                json.dump({'best_solution_parameters': best_params, 'best_solution_fitness_training': solution_fitness, 'validation_metrics': validation_metrics, 'test_metrics': test_metrics}, f, indent=4, cls=NpEncoder)
            logger.info(f"Saved GA results to {results_filename}")
            ga_instance.plot_fitness(save_dir=os.path.join(RESULTS_DIR, f"ga_fitness_plot_{datetime.now().strftime('%Y%m%d_%H%M%S')}"))
        
    except Exception as e:
        logger.critical(f"A critical error occurred in main_async_logic: {e}", exc_info=True)
    finally:
        if db_client: await db_client.close()
        logger.info("Optimizer async logic finished.")

# --- Entry Point Guard for Multiprocessing ---
if __name__ == "__main__":
    # `freeze_support()` is required for multiprocessing to work correctly on Windows.
    freeze_support()
    # Use a multiprocessing Manager to create shared data structures that can be
    # safely accessed by all parallel worker processes.
    with Manager() as manager:
        asyncio.run(main_async_logic(manager.dict(), manager.dict(), manager.dict(), manager.dict()))