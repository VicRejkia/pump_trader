document.addEventListener('DOMContentLoaded', () => {
    // Filter elements
    const applyFiltersBtn = document.getElementById('apply-filters-btn');
    const maxSocialsInput = document.getElementById('filter-max-socials');
    const maxRugcheckInput = document.getElementById('filter-max-rugcheck');
    const minVolumeInput = document.getElementById('filter-min-volume');
    const timeWindowSelect = document.getElementById('filter-time-window');
    const portfolioOnlyCheckbox = document.getElementById('filter-portfolio-only'); // Added

    // Chart elements
    const generateChartBtn = document.getElementById('generate-chart-btn');
    const mintsSelect = document.getElementById('mints-select');
    const chartDiv = document.getElementById('chart-div');
    const statusMessage = document.getElementById('status-message');

    // --- Filter Logic ---

    async function fetchAndPopulateTokens() {
        const maxSocials = maxSocialsInput.value;
        const maxRugcheck = maxRugcheckInput.value;
        const minVolume = minVolumeInput.value;
        const timeWindow = timeWindowSelect.value;
        const portfolioOnly = portfolioOnlyCheckbox.checked; // Added: Get checkbox state

        // Construct query parameters
        const queryParams = new URLSearchParams({
            max_socials: maxSocials,
            max_rugcheck: maxRugcheck,
            min_volume: minVolume,
            time_window: timeWindow,
            portfolio_only: portfolioOnly // Added: Include portfolio_only flag
        });

        statusMessage.textContent = 'Loading tokens based on filters...';
        mintsSelect.innerHTML = '<option value="" disabled>Loading...</option>'; // Clear and show loading

        try {
            const response = await fetch(`/api/filtered_tokens?${queryParams}`);
            if (!response.ok) {
                throw new Error(`HTTP error! Status: ${response.status}`);
            }
            const tokens = await response.json();

            mintsSelect.innerHTML = ''; // Clear loading/previous options

            if (tokens.length === 0) {
                mintsSelect.innerHTML = '<option value="" disabled>No tokens match the current filters.</option>';
                statusMessage.textContent = 'No tokens match the current filters.';
            } else {
                tokens.forEach(token => {
                    const option = document.createElement('option');
                    option.value = token.mint;
                    // Display name, scores, and mint
                    const rugcheckScore = token.rugcheck !== null ? token.rugcheck : 'N/A';
                    const socialsScore = token.socials !== null ? token.socials : 'N/A';
                    option.textContent = `${token.name} (Socials: ${socialsScore}, Rug: ${rugcheckScore}, Vol: ${token.volume}) - ${token.mint}`;
                    mintsSelect.appendChild(option);
                });
                statusMessage.textContent = `Loaded ${tokens.length} tokens. Select tokens and click 'Generate Chart'.`; // Updated status
            }

        } catch (error) {
            console.error('Error fetching filtered tokens:', error);
            mintsSelect.innerHTML = '<option value="" disabled>Error loading tokens.</option>';
            statusMessage.textContent = `Error loading tokens: ${error.message}`;
        }
    }

    // Event listener for the Apply Filters button
    applyFiltersBtn.addEventListener('click', fetchAndPopulateTokens);

    // Initial load of tokens when the page loads (using default filter values)
    fetchAndPopulateTokens();

    // --- Chart Generation Logic ---

    generateChartBtn.addEventListener('click', async () => {
        // Get selected options from the multi-select dropdown
        const selectedOptions = Array.from(mintsSelect.selectedOptions);
        const mintsArray = selectedOptions.map(option => option.value);

        if (mintsArray.length === 0) {
            statusMessage.textContent = 'Please select at least one token from the list.';
            Plotly.purge(chartDiv); // Clear previous chart
            return;
        }

        statusMessage.textContent = 'Loading chart data...';
        Plotly.purge(chartDiv); // Clear previous chart while loading

        try {
            const response = await fetch('/api/token_chart_data', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({ mints: mintsArray }),
            });

            if (!response.ok) {
                const errorData = await response.json().catch(() => ({ error: 'Failed to parse error response' }));
                throw new Error(`HTTP error! Status: ${response.status} - ${errorData.error || 'Unknown error'}`);
            }

            const chartData = await response.json();

            if (Object.keys(chartData).length === 0) {
                statusMessage.textContent = 'No chart data (trades or portfolio) found for the selected mint(s).';
                return;
            }

            const dataTraces = [];
            let hasDataToPlot = false; // Flag to check if there's anything to plot

            for (const mint in chartData) {
                if (chartData.hasOwnProperty(mint)) {
                    const mintData = chartData[mint];
                    const timeData = mintData.time || [];
                    const priceData = mintData.price_usd || [];
                    const buys = mintData.buys || [];
                    const sells = mintData.sells || [];

                    // Find the corresponding token name from the select options for the legend
                    const selectedOption = selectedOptions.find(opt => opt.value === mint);
                    // Extract name (part before the first parenthesis or the whole string)
                    let traceName = mint; // Fallback to mint
                    if (selectedOption) {
                        const nameMatch = selectedOption.textContent.match(/^([^(]+)/);
                        if (nameMatch) {
                            traceName = nameMatch[1].trim();
                        }
                    }


                    // Add main price line trace if data exists
                    if (timeData.length > 0 && priceData.length > 0) {
                        dataTraces.push({
                            x: timeData,
                            y: priceData,
                            mode: 'lines',
                            name: traceName // Use extracted name for legend
                        });
                        hasDataToPlot = true;
                    } else {
                         console.warn(`No main price line data for mint: ${mint}`);
                    }

                    // Add Buy Markers Trace
                    if (buys.length > 0) {
                        dataTraces.push({
                            x: buys.map(b => b.time),
                            y: buys.map(b => b.price_usd),
                            mode: 'markers',
                            type: 'scatter',
                            name: `${traceName} - Buys`,
                            marker: {
                                color: 'green',
                                symbol: 'triangle-up',
                                size: 10
                            }
                        });
                        hasDataToPlot = true;
                    }

                    // Add Sell Markers Trace
                    if (sells.length > 0) {
                        dataTraces.push({
                            x: sells.map(s => s.time),
                            y: sells.map(s => s.price_usd),
                            mode: 'markers',
                            type: 'scatter',
                            name: `${traceName} - Sells`,
                            marker: {
                                color: 'red',
                                symbol: 'triangle-down',
                                size: 10
                            }
                        });
                        hasDataToPlot = true;
                    }
                }
            }

            if (!hasDataToPlot) {
                 statusMessage.textContent = 'No chart data (trades or portfolio markers) found for the selected mint(s).';
                 return; // Exit if nothing was added to dataTraces
            }

            const layout = {
                title: 'Token Price vs. Elapsed Time (with Portfolio Buys/Sells)', // Updated title
                xaxis: {
                    title: 'Elapsed Time (minutes since first trade)' // Clarified x-axis
                },
                yaxis: {
                    title: 'Price (USD)',
                    // type: 'log', // Uncomment for log scale if needed
                    autorange: true // Ensure y-axis adjusts automatically
                },
                hovermode: 'closest',
                legend: { // Adjust legend position if needed
                    // yanchor: "top",
                    // y: 0.99,
                    // xanchor: "left",
                    // x: 0.01
                }
            };

            Plotly.newPlot(chartDiv, dataTraces, layout);
            statusMessage.textContent = 'Chart generated successfully.'; // Update status on success

        } catch (error) {
            console.error('Error fetching or plotting chart data:', error);
            statusMessage.textContent = `Error generating chart: ${error.message}`;
            Plotly.purge(chartDiv); // Clear chart on error
        }
    });
});