# ga_optimizer_module/ga_optimizer.py
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
import uuid
from multiprocessing import Manager, freeze_support, Process, Queue
from typing import Dict, List, Optional
from glob import glob
import gc  # For manual garbage collection

# --- Project Setup ---
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from bot_logger import logger, setup_logging
import config.config as bot_config
from config.ga_config import (
    OPTIMIZABLE_PARAMETERS, POPULATION_SIZE, NUM_GENERATIONS, CROSSOVER_PROBABILITY,
    MUTATION_PROBABILITY, FITNESS_METRIC, FITNESS_GOAL, DATA_SPLIT,
    BACKTEST_INITIAL_CAPITAL, RESULTS_DIR, HISTORICAL_DATA_START_TS,
    HISTORICAL_DATA_END_TS, MULTIPROCESSING_CORES, KEEP_ELITISM, PARENT_SELECTION_TYPE,
    CROSSOVER_TYPE, MUTATION_TYPE, GA_FITNESS_SAMPLE_SIZE, DETAILED_LOG_FILENAME, STOP_CRITERIA
)
from ga_optimizer_module.ga_backtester import run_backtest_sync
from utils import NpEncoder
from ga_optimizer_module.ga_ingestion import run_ingestion

# --- NEW: WORKER-LOCAL GLOBAL VARIABLES & CACHE PATH ---
WORKER_DATA = {}
GA_CACHE_PATH = os.path.join(project_root, "data", "ga_cache")

# --- Log Writer (Unchanged) ---
def log_writer_process(log_queue: Queue, log_file_path: str):
    records = []
    try:
        while True:
            record = log_queue.get()
            if record is None: break
            records.append(record)
        if records:
            df = pd.DataFrame(records)
            if 'parameters' in df.columns: df['parameters'] = df['parameters'].apply(json.dumps, cls=NpEncoder)
            if 'trade_history' in df.columns: df['trade_history'] = df['trade_history'].apply(json.dumps, cls=NpEncoder)
            df.to_parquet(log_file_path, index=False, engine='pyarrow')
            logger.debug(f"Successfully wrote {len(df)} records to {log_file_path}")
    except Exception as e:
        logger.debug(f"Log writer process error: {e}")

# --- Fitness Function (Loads from Parquet Cache) ---
def fitness_func_main_process(ga_instance, solution: np.ndarray, solution_idx: int) -> float:
    global WORKER_DATA
    worst_fitness = -float('inf') if FITNESS_GOAL == 'max' else float('inf')

    try:
        # --- ONE-TIME INITIALIZATION PER WORKER (FROM CACHE) ---
        if not WORKER_DATA:
            logger.debug(f"Worker PID {os.getpid()}: Initializing... Loading metadata (paths, lifespans, snapshots) from Parquet cache.")
            date_str = f"{HISTORICAL_DATA_START_TS.strftime('%Y%m%d')}_{HISTORICAL_DATA_END_TS.strftime('%Y%m%d')}"
            cache_dir = os.path.join(GA_CACHE_PATH, date_str)

            if not os.path.isdir(cache_dir):
                logger.debug(f"FATAL ERROR in Worker PID {os.getpid()}: Cache directory not found at '{cache_dir}'.")
                logger.debug("Please run 'python ga_optimizer_module/prepare_ga_dataset.py' first.")
                return worst_fitness
            
            # 1. Load mint-to-path for OHLCV (LAZY: don't load data yet)
            ohlcv_dir = os.path.join(cache_dir, "ohlcv_data")
            mint_to_path = {os.path.basename(f).replace('.parquet', ''): f for f in glob(os.path.join(ohlcv_dir, "*.parquet"))}
            all_mints = list(mint_to_path.keys())

            # 2. Load lifespans
            lifespans_df = pd.read_parquet(os.path.join(cache_dir, "token_lifespans.parquet"))
            token_lifespans = lifespans_df.to_dict(orient='index')
            
            # 3. Load DexScreener snapshots
            snapshots_dir = os.path.join(cache_dir, "dexscreener_snapshots")
            dexscreener_snapshots = {os.path.basename(f).replace('.parquet', ''): pd.read_parquet(f) for f in glob(os.path.join(snapshots_dir, "*.parquet"))}

            # Split data into train/validation/test sets
            all_mints = sorted(list(mint_to_path.keys()))
            random.Random(42).shuffle(all_mints) # Use a fixed seed for reproducibility
            train_ratio, val_ratio = DATA_SPLIT['training'], DATA_SPLIT['validation']
            train_idx = int(len(all_mints) * train_ratio)
            val_idx = int(len(all_mints) * (train_ratio + val_ratio))
            
            train_mints = all_mints[:train_idx]
            val_mints = all_mints[train_idx:val_idx]
            test_mints = all_mints[val_idx:]

            # Store paths for train set (lazy)
            WORKER_DATA['train_data_paths'] = {m: mint_to_path[m] for m in train_mints}
            WORKER_DATA['validation_data'] = {m: pd.read_parquet(mint_to_path[m]) for m in val_mints}
            WORKER_DATA['test_data'] = {m: pd.read_parquet(mint_to_path[m]) for m in test_mints}
            WORKER_DATA['lifespans'] = token_lifespans
            WORKER_DATA['snapshots'] = dexscreener_snapshots
            WORKER_DATA['train_mints'] = train_mints  # Store for sampling
            logger.debug(f"Worker PID {os.getpid()}: Loaded {len(WORKER_DATA['train_mints'])} train mints, {len(WORKER_DATA['validation_data'])} validation mints, {len(WORKER_DATA['test_data'])} test mints.")

        # --- REGULAR FITNESS CALCULATION ---
        train_mints = WORKER_DATA.get('train_mints', [])
        if not train_mints:
            logger.warning(f"Worker PID {os.getpid()}: No training mints available.")
            return worst_fitness
        
        parameters = {p['name']: p['type'](float(solution[i]) if p['type'] in [float, 'float'] else int(round(solution[i]))) for i, p in enumerate(OPTIMIZABLE_PARAMETERS)}
        
        sample_size = GA_FITNESS_SAMPLE_SIZE
        mints_to_evaluate = train_mints if not sample_size or sample_size >= len(train_mints) else random.sample(train_mints, min(sample_size, len(train_mints)))
        logger.debug(f"Worker PID {os.getpid()}: Evaluating solution {solution_idx} on {len(mints_to_evaluate)} mints (sample size: {sample_size})")

        fitness_values = []
        for mint in mints_to_evaluate:
            # Lazy load ONLY this mint's OHLCV data
            path = WORKER_DATA['train_data_paths'].get(mint)
            if not path or not os.path.exists(path):
                logger.warning(f"No Parquet file found for mint {mint}. Skipping.")
                continue
            df_data = pd.read_parquet(path)
            
            lifespan = WORKER_DATA['lifespans'].get(mint)
            snapshots = WORKER_DATA['snapshots'].get(mint)

            if df_data is None:
                logger.warning(f"No data loaded for mint {mint}. Skipping.")
                continue

            max_timestamp = lifespan['end_ts'] if lifespan else None
            parameters['mint'] = mint
            
            log_record = {
                "run_id": ga_instance.run_id,
                "generation": ga_instance.generations_completed,
                "solution_idx": solution_idx,
                "mint_tested": mint,
                "parameters": parameters,
                "status": "success"
            }
            try:
                result = run_backtest_sync(parameters, df_data, BACKTEST_INITIAL_CAPITAL, max_timestamp, snapshots, ga_instance.indicator_cache)
                if isinstance(result, dict):
                    log_record.update(result)
                    fitness = result.get(FITNESS_METRIC)
                    if fitness is not None and pd.notna(fitness) and np.isfinite(fitness):
                        fitness_values.append(float(fitness))
                else:
                    log_record.update({"status": "failed", "error_message": "Backtest returned invalid result."})
            except Exception as e:
                log_record.update({"status": "failed", "error_message": str(e)})
            finally:
                del df_data  # Free memory
                gc.collect()  # Force garbage collection

            ga_instance.log_queue.put(log_record)

        if not fitness_values:
            logger.warning(f"No valid backtests completed for solution {solution_idx}.")
            return worst_fitness
        average_fitness = np.mean(fitness_values)
        return average_fitness if np.isfinite(average_fitness) else worst_fitness

    except Exception as e:
        logger.debug(f"CRITICAL ERROR in worker PID {os.getpid()}: {e}")
        return worst_fitness

# --- PyGAD Callbacks (Unchanged) ---
def on_generation(ga_instance):
    generation = ga_instance.generations_completed
    if not hasattr(ga_instance, 'best_solutions_fitness') or not ga_instance.best_solutions_fitness:
        logger.warning(f"--- Generation {generation} Finished --- No valid solutions found yet.")
        return
    try:
        best_fitness = ga_instance.best_solutions_fitness[-1]
        avg_fitness_list = [f for f in ga_instance.last_generation_fitness if np.isfinite(f)]
        avg_fitness = np.mean(avg_fitness_list) if avg_fitness_list else 'N/A'
        avg_fitness_str = f"{avg_fitness:.6f}" if isinstance(avg_fitness, float) else avg_fitness
        logger.info(f"--- Generation {generation} Finished --- Best Fitness: {best_fitness:.6f} | Avg Fitness: {avg_fitness_str}")
        
        if generation > 0 and (generation % 5 == 0 or generation == ga_instance.num_generations):
            if ga_instance.best_solutions:
                best_solution = ga_instance.best_solutions[-1]
                best_params_dict = {p['name']: p['type'](float(best_solution[i]) if p['type'] in [float, 'float'] else int(round(best_solution[i]))) for i, p in enumerate(OPTIMIZABLE_PARAMETERS)}
                logger.info(f"Best Solution Parameters @ Gen {generation}:\n{json.dumps(best_params_dict, indent=2)}")
    except Exception as e:
        logger.error(f"Error in on_generation callback: {e}", exc_info=True)

# --- Final Evaluation Helper (Unchanged) ---
async def evaluate_solution(parameters: Dict, data_set_key: str, initial_capital: float, cache_for_eval: Optional[Dict] = None):
    logger.warning(f"Evaluation on '{data_set_key}' set is a placeholder. Full implementation should load from cache.")
    return {"data_set": data_set_key, "status": "placeholder"}

# --- Main Logic ---
async def main_async_logic(log_queue, shared_cache):
    setup_logging(logger_name="ga_optimizer_module")
    try:
        date_str = f"{HISTORICAL_DATA_START_TS.strftime('%Y%m%d')}_{HISTORICAL_DATA_END_TS.strftime('%Y%m%d')}"
        cache_dir = os.path.join(GA_CACHE_PATH, date_str)
        if not os.path.isdir(cache_dir):
            logger.critical(f"Cache directory not found: '{cache_dir}'")
            logger.critical("Please run 'python ga_optimizer_module/prepare_ga_dataset.py' to generate the required data cache.")
            return

        logger.info(f"Using pre-computed dataset from: {cache_dir}")
        
        optimization_run_id = str(uuid.uuid4())
        logger.info(f"Starting Optimization Run ID: {optimization_run_id}")
        
        # Validate OPTIMIZABLE_PARAMETERS
        for param in OPTIMIZABLE_PARAMETERS:
            param_name = param.get('name', 'Unnamed')
            param_type = param.get('type', float)
            if 'values' not in param and ('low' not in param or 'high' not in param):
                logger.error(f"Parameter {param_name} is missing 'values' or both 'low' and 'high'. Configuration: {param}")
                raise ValueError(f"Invalid parameter configuration for {param_name}")
            if param_type not in [float, int, bool, 'float', 'int', 'bool']:
                logger.error(f"Parameter {param_name} has invalid type '{param_type}'. Must be float, int, bool, 'float', 'int', or 'bool'. Configuration: {param}")
                raise ValueError(f"Invalid parameter type for {param_name}")

        gene_space = [{'low': p['low'], 'high': p['high']} if 'low' in p else p['values'] for p in OPTIMIZABLE_PARAMETERS]
        num_processes = os.cpu_count() - 2 if MULTIPROCESSING_CORES == "auto" and os.cpu_count() and os.cpu_count() > 2 else int(MULTIPROCESSING_CORES)
        
        # --- Population Seeding Logic ---
        logger.info("Building a seeded initial population...")
        initial_population = []
        
        seed_solution = []
        for param in OPTIMIZABLE_PARAMETERS:
            param_name = param['name']
            if hasattr(bot_config, param_name):
                value = getattr(bot_config, param_name)
                if isinstance(value, tuple) and len(value) == 1: value = value[0]
                if isinstance(value, bool): value = int(value)
                seed_solution.append(value)
            else:
                if 'values' in param:
                    seed_solution.append(param['values'][len(param['values']) // 2])
                else:
                    seed_solution.append((param.get('low', 0) + param.get('high', 0)) / 2)
        initial_population.append(seed_solution)

        num_to_generate = POPULATION_SIZE - 1
        for i in range(num_to_generate):
            new_solution = list(seed_solution)
            num_mutations = max(1, int(len(new_solution) * 0.20))
            for _ in range(num_mutations):
                gene_idx = random.randrange(len(new_solution))
                param_space = OPTIMIZABLE_PARAMETERS[gene_idx]
                if 'values' in param_space:
                    new_gene = random.choice(param_space['values'])
                else:
                    low, high = param_space.get('low', 0), param_space.get('high', 1)
                    new_gene = random.uniform(low, high)
                new_solution[gene_idx] = param_space['type'](new_gene)
            initial_population.append(new_solution)
        logger.info(f"Seeded population of {len(initial_population)} individuals created.")
        
        ga_instance = pygad.GA(
            num_generations=NUM_GENERATIONS, 
            num_parents_mating=max(2, int(POPULATION_SIZE * 0.3)), 
            fitness_func=fitness_func_main_process, 
            sol_per_pop=POPULATION_SIZE, 
            num_genes=len(OPTIMIZABLE_PARAMETERS), 
            initial_population=initial_population,
            gene_space=gene_space, 
            parent_selection_type=PARENT_SELECTION_TYPE, 
            crossover_type=CROSSOVER_TYPE, 
            crossover_probability=CROSSOVER_PROBABILITY, 
            mutation_type=MUTATION_TYPE, 
            mutation_probability=MUTATION_PROBABILITY, 
            keep_elitism=max(0, KEEP_ELITISM), 
            on_generation=on_generation, 
            parallel_processing=['process', num_processes], 
            stop_criteria=STOP_CRITERIA
        )
        
        ga_instance.log_queue = log_queue
        ga_instance.indicator_cache = shared_cache
        ga_instance.run_id = optimization_run_id

        logger.info(f"--- Starting GA Optimization ({num_processes} processes) ---")
        start_time = time.time()
        ga_instance.run()
        logger.info(f"--- GA Optimization Finished (Duration: {(time.time() - start_time)/60:.2f} minutes) ---")
        
        # --- Save Best Solution to JSON ---
        if hasattr(ga_instance, 'best_solution_generation') and ga_instance.best_solution_generation != -1:
            solution, solution_fitness, solution_idx = ga_instance.best_solution()
            
            logger.info(f"Best solution found at generation {ga_instance.best_solution_generation} with fitness: {solution_fitness}")
            
            best_params_dict = {
                p['name']: p['type'](float(solution[i]) if p['type'] in [float, 'float'] else int(round(solution[i])))
                for i, p in enumerate(OPTIMIZABLE_PARAMETERS)
            }
            
            # Construct the final JSON object
            results_to_save = {
                "best_solution_id": f"gen{ga_instance.best_solution_generation}_idx{solution_idx}",
                "best_solution_parameters": best_params_dict,
                "best_solution_fitness_training": solution_fitness,
                "validation_metrics": {"status": "not_run"},
                "test_metrics": {"status": "not_run"}
            }
            
            # Generate filename and save
            date_today_str = datetime.now().strftime("%Y%m%d")
            filename = f"ga_results_{date_today_str}_{optimization_run_id}.json"
            output_path = os.path.join(RESULTS_DIR, filename)
            
            try:
                with open(output_path, 'w') as f:
                    json.dump(results_to_save, f, indent=4, cls=NpEncoder)
                logger.info(f"✅ Successfully saved best parameters to {output_path}")
            except Exception as e:
                logger.error(f"Failed to save best parameters to JSON: {e}", exc_info=True)
        else:
            logger.warning("No best solution was found or recorded by the GA instance. Skipping JSON export.")

    except Exception as e:
        logger.critical(f"A critical error occurred in main_async_logic: {e}", exc_info=True)
    finally:
        logger.info("Optimizer async logic finished.")

# --- Entry Point (Unchanged) ---
if __name__ == "__main__":
    freeze_support()
    with Manager() as manager:
        log_queue = manager.Queue()
        shared_cache = manager.dict() # Indicator cache can still be shared
        
        os.makedirs(RESULTS_DIR, exist_ok=True)
        log_file_path = os.path.join(RESULTS_DIR, DETAILED_LOG_FILENAME)
        
        log_process = Process(target=log_writer_process, args=(log_queue, log_file_path))
        log_process.start()
        
        try:
            asyncio.run(main_async_logic(log_queue, shared_cache))
        finally:
            logger.info("Main logic finished. Shutting down logger process...")
            log_queue.put(None); log_process.join()
            logger.info("Logger process has been shut down.")

        logger.info("--- Starting Automatic Database Ingestion ---")
        try:
            if os.path.exists(log_file_path): 
                asyncio.run(run_ingestion(log_file_path))
                logger.info("--- Database Ingestion Completed Successfully ---")
        except Exception as e:
            logger.error(f"DB ingestion failed: {e}", exc_info=True)
        logger.info("Open GA Dashboard with: 'streamlit run ga_optimizer_module/ga_dashboard.py'")