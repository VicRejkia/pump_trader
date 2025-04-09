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
    const tokenListContainer = document.getElementById('token-list-container'); // Changed from mints-select
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
        tokenListContainer.innerHTML = '<div class="list-group-item">Loading...</div>'; // Clear and show loading

        try {
            const response = await fetch(`/api/filtered_tokens?${queryParams}`);
            if (!response.ok) {
                throw new Error(`HTTP error! Status: ${response.status}`);
            }
            const tokens = await response.json();

            tokenListContainer.innerHTML = ''; // Clear loading/previous options

            if (tokens.length === 0) {
                tokenListContainer.innerHTML = '<div class="list-group-item">No tokens match the current filters.</div>';
                statusMessage.textContent = 'No tokens match the current filters.';
            } else {
                tokens.forEach(token => {
                    const listItem = document.createElement('label'); // Use label for better checkbox click handling
                    listItem.className = 'list-group-item d-flex justify-content-between align-items-center';

                    const checkbox = document.createElement('input');
                    checkbox.type = 'checkbox';
                    checkbox.className = 'form-check-input me-2';
                    checkbox.value = token.mint;
                    checkbox.setAttribute('data-token-name', token.name); // Store name for chart legend

                    const textContainer = document.createElement('div');
                    textContainer.style.flexGrow = '1'; // Allow text to take available space

                    const nameSpan = document.createElement('span');
                    nameSpan.textContent = `${token.name} `;
                    nameSpan.style.fontWeight = 'bold';

                    const detailsSpan = document.createElement('small');
                    const rugcheckScore = token.rugcheck !== null ? token.rugcheck : 'N/A';
                    const socialsScore = token.socials !== null ? token.socials : 'N/A';
                    detailsSpan.textContent = `(Socials: ${socialsScore}, Rug: ${rugcheckScore}, Vol: ${token.volume}) `;
                    detailsSpan.className = 'text-muted me-2';

                    const mintSpan = document.createElement('span');
                    mintSpan.textContent = token.mint;
                    mintSpan.className = 'badge bg-secondary copy-mint'; // Style as badge, add class for copy
                    mintSpan.style.cursor = 'pointer';
                    mintSpan.title = 'Click to copy mint address';
                    mintSpan.setAttribute('data-mint', token.mint); // Store mint in data attribute

                    // Add click listener for copying
                    mintSpan.addEventListener('click', (e) => {
                        e.preventDefault(); // Prevent label from toggling checkbox
                        e.stopPropagation(); // Prevent label from toggling checkbox
                        copyToClipboard(token.mint, mintSpan);
                    });

                    textContainer.appendChild(checkbox);
                    textContainer.appendChild(nameSpan);
                    textContainer.appendChild(detailsSpan);
                    textContainer.appendChild(mintSpan);

                    listItem.appendChild(textContainer);
                    tokenListContainer.appendChild(listItem);
                });
                statusMessage.textContent = `Loaded ${tokens.length} tokens. Check tokens and click 'Generate Chart'.`; // Updated status
            }

        } catch (error) {
            console.error('Error fetching filtered tokens:', error);
            tokenListContainer.innerHTML = '<div class="list-group-item">Error loading tokens.</div>';
            statusMessage.textContent = `Error loading tokens: ${error.message}`;
        }
    }

    // Event listener for the Apply Filters button
    applyFiltersBtn.addEventListener('click', fetchAndPopulateTokens);

    // Initial load of tokens when the page loads (using default filter values)
    fetchAndPopulateTokens();

    // --- Clipboard Copy Function ---
    async function copyToClipboard(text, element) {
        try {
            await navigator.clipboard.writeText(text);
            const originalText = element.textContent;
            element.textContent = 'Copied!';
            element.classList.remove('bg-secondary');
            element.classList.add('bg-success');
            setTimeout(() => {
                element.textContent = originalText;
                element.classList.remove('bg-success');
                element.classList.add('bg-secondary');
            }, 1500); // Revert after 1.5 seconds
        } catch (err) {
            console.error('Failed to copy: ', err);
            const originalText = element.textContent;
            element.textContent = 'Error!';
             element.classList.remove('bg-secondary');
            element.classList.add('bg-danger');
             setTimeout(() => {
                element.textContent = originalText;
                element.classList.remove('bg-danger');
                element.classList.add('bg-secondary');
            }, 1500);
        }
    }

    // --- Chart Generation Logic ---

    generateChartBtn.addEventListener('click', async () => {
        // Get selected mints from checked checkboxes
        const selectedCheckboxes = tokenListContainer.querySelectorAll('input[type="checkbox"]:checked');
        const mintsArray = Array.from(selectedCheckboxes).map(checkbox => checkbox.value);

        if (mintsArray.length === 0) {
            statusMessage.textContent = 'Please check at least one token from the list.';
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

                    // Find the corresponding checkbox to get the token name stored in data attribute
                    const selectedCheckbox = Array.from(selectedCheckboxes).find(cb => cb.value === mint);
                    let traceName = mint; // Fallback to mint
                    if (selectedCheckbox) {
                        traceName = selectedCheckbox.getAttribute('data-token-name') || mint;
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