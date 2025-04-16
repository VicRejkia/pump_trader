# Plan for: **Genetic Algorithms (GA) / Evolutionary Strategies**

**Goal:** To evolve sets of trading parameters (constants from `config.py`) that yield the best historical performance according to a defined fitness metric (e.g., Profitability, Risk-Adjusted Return).

## **Phase 1: Setup and Data Preparation**

1. **Identify Optimizable Parameters & Define Ranges:**
    * **Action:** Go through `config.py` and list every constant you want the GA to optimize.
    * **Constants:** Examples include `SOL_TO_BUY`, `INITIAL_STOP_LOSS_PERCENT`[cite: 2], `FIRST_SELL_PERCENT`[cite: 3], `TRAILING_STOP_LOSS_PERCENT`[cite: 3], `SECOND_TAKE_PROFIT_PERCENT`[cite: 3], `FIRST_SELL_PROFIT_MARGIN`[cite: 4], `DEFAULT_VOLUME_THRESHOLD`[cite: 5], `DEFAULT_MARKETCAP_THRESHOLD`[cite: 6], `MIN_VOLATILITY`[cite: 6], etc.
    * **Define Ranges:** For each parameter, define a sensible minimum and maximum value. This prevents the GA from exploring unrealistic values (e.g., stop-loss > 100%, negative buy amount). *Example:* `INITIAL_STOP_LOSS_PERCENT`: Range [5.0, 95.0].

2. **Historical Data Extraction:**
    * **Action:** Enhance or create functions within `database_handler.py` [cite: 13] to efficiently fetch comprehensive historical data required for backtesting.
    * **Data Needed:**
        * Token price history (from `v_trades` view [cite: 747]).
        * Volume data (from `v_trades` view [cite: 747]).
        * Market Cap data (from `v_trades` view [cite: 747]).
        * RugCheck scores over time (from `v_rugcheck` view [cite: 749]).
        * Socials scores over time (from `v_tokens` view [cite: 746]).
        * Token creation timestamps (`v_tokens` table [cite: 707]).
    * **Structure:** Fetch data token by token or load relevant time-series data into memory/files suitable for the backtester (e.g., pandas DataFrames). Ensure timestamps are consistent (UTC)[cite: 31].

3. **Data Splitting:**
    * **Action:** Divide your historical data into distinct chronological periods:
        * **Training Set:** Used by the GA's fitness function (backtester) to evaluate individuals. (e.g., 60% of data)
        * **Validation Set:** Used to check the best individual found during training for overfitting *after* the GA run is complete. (e.g., 20% of data)
        * **Test Set:** Used for a final, unbiased evaluation of the chosen parameters *after* validation. (e.g., 20% of data)
    * **Importance:** This prevents overfitting, where the GA finds parameters that work exceptionally well on the training data but fail on unseen data.

## **Phase 2: Backtesting Engine Development**

1. **Create Backtester Module:**
    * **Action:** Develop a new Python module (e.g., `backtester.py`) or significantly refactor `trading_logic.py`.
    * **Core Function:** `run_backtest(parameters: dict, historical_data: object) -> dict`
2. **Simulate Trading Logic:**
    * **Action:** The `run_backtest` function must simulate the core decision-making process from `trading_logic.py` [cite: 508] (`check_trading_opportunities`, `check_sell_opportunities`, `execute_buy`, `execute_sell`) but using the *input `parameters`* instead of `config.py` values and operating on the *provided `historical_data`* segment.
    * **State Simulation:** Mimic portfolio state changes (active positions, remaining tokens, PnL) similar to how `state_manager.py` [cite: 456, 457] and `portfolio` table [cite: 719] track it, but purely based on the historical data feed.
3. **Calculate Performance Metrics:**
    * **Action:** The backtester must return a dictionary of performance metrics calculated over the simulation period.
    * **Metrics:** Essential: Total PnL, Max Drawdown. Good to have: Sharpe Ratio, Sortino Ratio, Win Rate, Average Profit/Loss per trade, Number of Trades.

## **Phase 3: Genetic Algorithm Implementation**

1. **Choose a GA Library:**
    * **Action:** Select a suitable Python library. `DEAP` is powerful but can be complex. `PyGAD` is often easier for beginners.
2. **Chromosome Representation:**
    * **Action:** Define how an "individual" (a set of parameters) is represented. A list or dictionary where each element corresponds to a parameter identified in Phase 1, Step 1 is common.
3. **Population Initialization:**
    * **Action:** Create an initial population (e.g., 50-100 individuals) where each individual has parameter values randomly chosen within the ranges defined in Phase 1, Step 1.
4. **Fitness Function:**
    * **Action:** Create the function that the GA library will use to evaluate each individual.
    * **Logic:** This function takes an individual (chromosome/parameter set) as input, calls `run_backtest` from Phase 2 using the **Training Data Set**, and returns a single numerical fitness score.
    * **Score Choice:** Decide on the primary metric to optimize (e.g., return Sharpe Ratio for risk-adjusted return, or Total PnL for absolute profit).
5. **Genetic Operators:**
    * **Action:** Configure the GA library's operators:
        * **Selection:** Choose how "parents" are selected for breeding (e.g., Tournament Selection, Rank Selection).
        * **Crossover:** Choose how parent chromosomes combine (e.g., Single-Point, Uniform Crossover). Define a crossover probability (e.g., 70-90%).
        * **Mutation:** Choose how offspring chromosomes are randomly altered (e.g., Gaussian mutation for numerical parameters, random reset within range). Define a mutation probability (e.g., 5-20%).
6. **GA Execution Loop:**
    * **Action:** Configure and run the GA's evolution loop provided by the library.
    * **Parameters:** Set population size, number of generations, crossover/mutation probabilities.
7. **Termination Criteria:**
    * **Action:** Define when the GA stops evolving (e.g., after a fixed number of generations, or when the best fitness score hasn't improved for a certain number of generations).

## **Phase 4: Integration and Evaluation**

1. **Extract Best Parameters:**
    * **Action:** After the GA finishes, identify the individual (chromosome) with the best fitness score on the **Training Set**.
2. **Validation:**
    * **Action:** Take the best parameter set found and run it through the backtester using the **Validation Data Set**.
    * **Analysis:** Compare the performance on the validation set to the training set. A significant drop indicates potential overfitting. If overfit, you might need to adjust GA parameters (e.g., increase population size, adjust mutation rate), use simpler fitness metrics, or get more data.
3. **Parameter Integration:**
    * **Action:** Implement a way for the main bot (`trading_bot.py` [cite: 481]) to load these validated, optimized parameters at startup. This could be from a file (JSON, YAML) or a dedicated database table. The loaded parameters would then be passed to `TradingManager` [cite: 509] or used to override defaults.
4. **Final Testing:**
    * **Action:** Run the backtester with the chosen parameters on the **Test Data Set** (completely unseen data) to get a final, unbiased estimate of real-world performance expectancy.
5. **Deployment & Monitoring:**
    * **Action:** Start with paper trading using the optimized parameters. If results are satisfactory, consider live deployment.
    * **Retraining:** Market conditions change. Plan to periodically re-run the entire GA optimization process (e.g., quarterly, monthly) using updated historical data to keep parameters relevant.

## **Potential Challenges:**

* **Computational Cost:** Backtesting can be slow, and running it hundreds or thousands of times for the GA can take significant time. Consider parallelization or cloud computing.
* **Overfitting:** The GA might find parameters perfectly tuned to historical quirks that won't repeat. Rigorous validation and testing are crucial.
* **Data Quality:** The quality of the optimization depends heavily on the quality and completeness of your historical data.
