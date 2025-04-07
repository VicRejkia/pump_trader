document.addEventListener('DOMContentLoaded', () => {
    const generateBtn = document.getElementById('generate-chart-btn');
    const mintsSelect = document.getElementById('mints-select'); // Changed from mints-input
    const chartDiv = document.getElementById('chart-div');
    const statusMessage = document.getElementById('status-message');

    generateBtn.addEventListener('click', async () => {
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
                statusMessage.textContent = 'No trade data found for the specified mint(s).';
                return;
            }

            const dataTraces = [];
            for (const mint in chartData) {
                if (chartData.hasOwnProperty(mint)) {
                    dataTraces.push({
                        x: chartData[mint].time,
                        y: chartData[mint].price,
                        mode: 'lines',
                        name: mint // Use mint address as the trace name
                    });
                }
            }

            const layout = {
                title: 'Token Price vs. Elapsed Time',
                xaxis: {
                    title: 'Elapsed Time (minutes)'
                },
                yaxis: {
                    title: 'Price',
                    // Optionally set y-axis to logarithmic scale if prices vary widely
                    // type: 'log',
                    // autorange: true
                },
                hovermode: 'closest' // Improve hover interaction
            };

            Plotly.newPlot(chartDiv, dataTraces, layout);
            statusMessage.textContent = ''; // Clear status message on success

        } catch (error) {
            console.error('Error fetching or plotting chart data:', error);
            statusMessage.textContent = `Error: ${error.message}`;
            Plotly.purge(chartDiv); // Clear chart on error
        }
    });
});