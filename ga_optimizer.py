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
from datetime import datetime, timezone
import time
import json
from multiprocessing import Pool
from itertools import islice
import nest_asyncio

from logger import logger, setup_logging
from ga_config import (
    OPTIMIZABLE_PARAMETERS, POPULATION_SIZE, NUM_GENERATIONS,
    CROSSOVER_PROBABILITY, MUTATION_PROBABILITY, FITNESS_METRIC, FITNESS_GOAL,
    DATA_SPLIT, BACKTEST_INITIAL_CAPITAL,
    HISTORICAL_DATA_START_TS, HISTORICAL_DATA_END_TS
)
from database_handler import DatabaseClient
from backtester import run_backtest

# Global variables
historical_data_sets = {}
db_client = None

nest_asyncio.apply()


def ensure_datetime(dt):
    """Ensure the input is a timezone-aware datetime object."""
    if isinstance(dt, datetime):
        return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)
    if isinstance(dt, str):
        return datetime.strptime(dt, "%Y-%m-%d").replace(tzinfo=timezone.utc)
    raise ValueError(f"Unsupported date format: {dt}")


def batch_parameters(parameters, batch_size):
    """Split parameters into smaller batches."""
    it = iter(parameters)
    for i in range(0, len(parameters), batch_size):
        yield list(islice(it, batch_size))


async def load_and_split_data(start_date_str: str, end_date_str: str):
    """Load historical data and split it into training, validation, and test sets."""
    global historical_data_sets, db_client
    if not db_client:
        logger.error("Database client not initialized.")
        return False

    try:
        start_date = ensure_datetime(start_date_str)
        end_date = ensure_datetime(end_date_str)
        logger.info(f"Loading data from {start_date} to {end_date}")

        query_mints_in_period = """
            SELECT DISTINCT mint FROM v_trades
            WHERE timestamp >= $1 AND timestamp < $2;
        """
        active_mints_records = await db_client.pool.fetch(query_mints_in_period, start_date, end_date)
        if not active_mints_records:
            logger.error("No tokens found with trades in the specified period.")
            return False
        mints_to_load = [r['mint'] for r in active_mints_records]

        all_historical_data = await db_client.get_historical_data_for_backtesting(mints_to_load, start_date, end_date)
        if not all_historical_data:
            logger.error("Failed to fetch historical data.")
            return False

        historical_data_sets = {'train': {}, 'validation': {}, 'test': {}}
        total_duration = end_date - start_date
        train_end = start_date + total_duration * DATA_SPLIT['training']
        validation_end = train_end + total_duration * DATA_SPLIT['validation']

        for mint, df in all_historical_data.items():
            if df.empty or not isinstance(df.index, pd.DatetimeIndex):
                continue
            df_train = df[df.index < train_end].copy()
            df_validation = df[(df.index >= train_end) & (df.index < validation_end)].copy()
            df_test = df[df.index >= validation_end].copy()

            if not df_train.empty:
                historical_data_sets['train'][mint] = df_train
                if not df_validation.empty:
                    historical_data_sets['validation'][mint] = df_validation
                if not df_test.empty:
                    historical_data_sets['test'][mint] = df_test

        if not historical_data_sets['train']:
            logger.error("No training data available.")
            return False

        return True

    except Exception as e:
        logger.exception(f"Error loading data: {e}")
        return False

def run_backtest_sync(task):
    """Run backtest synchronously."""
    parameters, df_data, initial_capital = task
    return asyncio.run(run_backtest(parameters, df_data, initial_capital))

async def run_backtest_for_fitness(solutions, data_set_key='train', batch=None):
    """Run backtests for a batch of solutions."""
    fitness_results = []
    data_for_backtest = historical_data_sets.get(data_set_key, {})
    if not data_for_backtest:
        return [-float('inf') if FITNESS_GOAL == 'max' else float('inf')] * len(solutions)

    tasks_to_run = []
    solution_indices = []

    for sol_idx, solution in enumerate(solutions):
        # Debugging: Log the batch and solution
        logger.debug(f"Batch: {batch}")
        logger.debug(f"Solution: {solution}")

        # Use the current batch of parameters instead of the full OPTIMIZABLE_PARAMETERS
        parameters = {param['name']: solution[i] for i, param in enumerate(batch)}
        logger.debug(f"Parameters: {parameters}")

        for mint, df_data in data_for_backtest.items():
            if df_data.empty:
                continue
            tasks_to_run.append((parameters.copy(), df_data.copy(), BACKTEST_INITIAL_CAPITAL))
            solution_indices.append(sol_idx)

    # Use multiprocessing to run backtests in parallel
    with Pool() as pool:
        backtest_raw_results = pool.map(run_backtest_sync, tasks_to_run)

    aggregated_fitness = {i: {'total': 0.0, 'count': 0} for i in range(len(solutions))}
    for i, result in enumerate(backtest_raw_results):
        original_sol_idx = solution_indices[i]
        if isinstance(result, dict):
            fitness_value = result.get(FITNESS_METRIC)
            if fitness_value is not None and not pd.isna(fitness_value):
                aggregated_fitness[original_sol_idx]['total'] += fitness_value
                aggregated_fitness[original_sol_idx]['count'] += 1

    for sol_idx in range(len(solutions)):
        total = aggregated_fitness[sol_idx]['total']
        count = aggregated_fitness[sol_idx]['count']
        avg_fitness = total / count if count > 0 else -float('inf') if FITNESS_GOAL == 'max' else float('inf')
        fitness_results.append(avg_fitness)

    return fitness_results


def create_fitness_func_wrapper(batch):
    """Create a fitness function wrapper that captures the batch."""
    def fitness_func_wrapper(ga_instance, solution, solution_idx):
        """Wrapper for the fitness function."""
        try:
            # Pass the batch to the backtest function
            results = asyncio.run(run_backtest_for_fitness([solution], data_set_key='train', batch=batch))
            return results[0] if results else -float('inf')
        except Exception as e:
            logger.exception(f"Error in fitness function for solution {solution_idx}: {e}")
            return -float('inf')
    return fitness_func_wrapper

async def main():
    global db_client
    setup_logging()

    db_client = DatabaseClient()
    try:
        await db_client.connect()
    except Exception as e:
        logger.critical(f"Failed to connect to database: {e}")
        return

    if not await load_and_split_data(HISTORICAL_DATA_START_TS, HISTORICAL_DATA_END_TS):
        await db_client.close()
        return

    batches = list(batch_parameters(OPTIMIZABLE_PARAMETERS, batch_size=3))

    for batch_idx, batch in enumerate(batches):
        logger.info(f"Running GA for batch {batch_idx + 1}/{len(batches)}: {[param['name'] for param in batch]}")

        gene_space = [param['values'] for param in batch]
        gene_type = [param['type'] for param in batch]

        def on_generation(ga_instance):
            generation = ga_instance.generations_completed
            best_fitness = ga_instance.best_solution(pop_fitness=ga_instance.last_generation_fitness)[1]
            logger.info(f"Generation {generation} finished. Best Fitness: {best_fitness:.4f}")

        # Create the fitness function wrapper with the current batch
        fitness_func_wrapper = create_fitness_func_wrapper(batch)

        ga_instance = pygad.GA(
            num_generations=NUM_GENERATIONS,
            num_parents_mating=int(POPULATION_SIZE * 0.25),
            fitness_func=fitness_func_wrapper,
            sol_per_pop=POPULATION_SIZE,
            num_genes=len(batch),
            gene_space=gene_space,
            gene_type=gene_type,
            parent_selection_type="sss",
            crossover_type="single_point",
            crossover_probability=CROSSOVER_PROBABILITY,
            mutation_type="random",
            mutation_probability=MUTATION_PROBABILITY,
            mutation_by_replacement=True,
            keep_elitism=2,
            on_generation=on_generation
        )

        ga_instance.run()

        solution, solution_fitness, _ = ga_instance.best_solution()
        best_params = {param['name']: solution[i] for i, param in enumerate(batch)}
        logger.info(f"Best solution for batch {batch_idx + 1}: {json.dumps(best_params, indent=4)}")

    await db_client.close()


if __name__ == "__main__":
    asyncio.run(main())