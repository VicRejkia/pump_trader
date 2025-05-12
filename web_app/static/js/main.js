$(document).ready(function() {
    const mainContentArea = $('#dynamic-content-placeholder');
    const pageTitle = $('#page-title');
    const logDisplay = $('#log-display');
    let logInterval;
    let statusInterval;
    let currentChart = null; // To keep track of the current TradingView chart instance

    function loadPage(pageName) {
        console.log(`Loading page: ${pageName}`);
        mainContentArea.html('<p>Loading...</p>'); // Show loading indicator
        $.ajax({
            url: `/page/${pageName}`,
            method: 'GET',
            success: function(data) {
                mainContentArea.html(data);
                pageTitle.text(pageName.charAt(0).toUpperCase() + pageName.slice(1));
                // Activate functions specific to the loaded page
                if (pageName === 'dashboard') {
                    loadDashboardData();
                    if (statusInterval) clearInterval(statusInterval);
                    statusInterval = setInterval(loadDashboardData, 5000); // Refresh every 5s
                } else if (pageName === 'config') {
                    loadConfigData();
                    if (statusInterval) clearInterval(statusInterval);
                } else if (pageName === 'charts') {
                    loadTokensForChart();
                    if (statusInterval) clearInterval(statusInterval);
                }
            },
            error: function(xhr, status, error) {
                mainContentArea.html(`<p class="text-danger">Error loading page: ${error}</p>`);
                console.error("Error loading page:", status, error);
            }
        });
    }

    // --- Dashboard Functions ---
    function loadDashboardData() {
        $.getJSON('/api/status', function(data) {
            if (data.error) {
                console.error("Error fetching bot status:", data.error);
                $('#bot-file-status').text('Error');
                // Handle other fields similarly
                return;
            }
            $('#bot-uptime').text(data.uptime || 'N/A');
            $('#bot-asyncio-tasks').text(data.asyncio_tasks || 'N/A');
            $('#bot-token-subscriptions').text(data.token_subscriptions_count || 'N/A');
            $('#bot-sol-balance').text(data.current_sol_balance || 'N/A');
            $('#bot-file-status').text(data.bot_file_status || 'N/A');
        }).fail(function(jqXHR, textStatus, errorThrown) {
            console.error("Failed to load dashboard data:", textStatus, errorThrown);
            $('#bot-uptime').text('Error loading status');
        });
    }

    // --- Configuration Page Functions ---
    function loadConfigData() {
        const container = $('#config-parameters-container');
        container.html('<p>Loading configuration...</p>');
        $.getJSON('/api/config', function(config) {
            if (config.error) {
                container.html(`<p class="text-danger">Error loading config: ${config.error}</p>`);
                return;
            }
            let formHtml = '';
            for (const key in config) {
                if (config.hasOwnProperty(key)) {
                    const value = config[key];
                    let inputType = 'text';
                    if (typeof value === 'number') {
                        inputType = 'number';
                    } else if (typeof value === 'boolean') {
                        inputType = 'checkbox';
                    }

                    formHtml += `<div class="form-group row">
                                    <label for="config-${key}" class="col-sm-4 col-form-label">${key.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase())}</label>
                                    <div class="col-sm-8">`;
                    if (inputType === 'checkbox') {
                        formHtml += `<input type="${inputType}" class="form-check-input" id="config-${key}" name="${key}" ${value ? 'checked' : ''}>`;
                    } else if (Array.isArray(value) || typeof value === 'object' && value !== null && !(value instanceof String)) { // Handle lists/sets/objects as JSON string
                        formHtml += `<textarea class="form-control" id="config-${key}" name="${key}" rows="3">${JSON.stringify(value, null, 2)}</textarea>`;
                        formHtml += `<small class="form-text text-muted">Enter as a valid JSON list/object (e.g., ["item1", "item2"] or {"key": "value"}).</small>`;
                    }
                    else {
                        formHtml += `<input type="${inputType}" class="form-control" id="config-${key}" name="${key}" value="${value}">`;
                    }
                    formHtml += `   </div>
                                </div>`;
                }
            }
            container.html(formHtml);
        }).fail(function() {
            container.html('<p class="text-danger">Failed to load configuration.</p>');
        });
    }

    $('#main-content-area').on('submit', '#config-form', function(event) {
        event.preventDefault();
        const formData = $(this).serializeArray();
        const configUpdates = {};
        const statusDiv = $('#config-save-status');

        formData.forEach(function(item) {
            // Try to parse numbers, otherwise keep as string
            let value = item.value;
            if ($(`#config-${item.name}`).attr('type') === 'number') {
                value = parseFloat(item.value);
            } else if ($(`#config-${item.name}`).attr('type') === 'checkbox') {
                value = $(`#config-${item.name}`).is(':checked');
            } else if ($(`#config-${item.name}`).is('textarea')) { // For JSON strings
                try {
                    value = JSON.parse(item.value);
                } catch (e) {
                    statusDiv.html(`<div class="alert alert-danger">Error parsing JSON for ${item.name}: ${e.message}</div>`);
                    // Potentially highlight the textarea or return early
                    return; // Or throw an error to stop submission
                }
            }
            configUpdates[item.name] = value;
        });
        // Handle unchecked checkboxes (they are not sent by default)
        $(this).find('input[type="checkbox"]:not(:checked)').each(function() {
            configUpdates[$(this).attr('name')] = false;
        });


        statusDiv.html('<div class="alert alert-info">Saving configuration...</div>');

        $.ajax({
            url: '/api/config/update',
            method: 'POST',
            contentType: 'application/json',
            data: JSON.stringify(configUpdates),
            success: function(response) {
                statusDiv.html(`<div class="alert alert-success">${response.message}</div>`);
                loadConfigData(); // Refresh displayed config
            },
            error: function(xhr) {
                const errorMsg = xhr.responseJSON ? xhr.responseJSON.error : 'Failed to save configuration.';
                statusDiv.html(`<div class="alert alert-danger">${errorMsg}</div>`);
            }
        });
    });

    // --- Charts Page Functions ---
    function loadTokensForChart() {
        const tokenSelect = $('#token-select');
        tokenSelect.html('<option value="">Loading tokens...</option>');
        $.getJSON('/api/tokens', function(tokens) {
            if (tokens.error) {
                tokenSelect.html(`<option value="">Error: ${tokens.error}</option>`);
                return;
            }
            if (tokens.length === 0) {
                tokenSelect.html('<option value="">No tokens found</option>');
                return;
            }
            tokenSelect.empty().append('<option value="">Select a token</option>');
            tokens.forEach(function(token) {
                tokenSelect.append(`<option value="${token.mint}">${token.name || token.mint} (${token.symbol || 'N/A'})</option>`);
            });
        }).fail(function() {
            tokenSelect.html('<option value="">Failed to load tokens</option>');
        });
    }

    $('#main-content-area').on('change', '#token-select', function() {
        const mintAddress = $(this).val();
        if (mintAddress) {
            loadTradingViewChart(mintAddress);
        } else {
            if (currentChart) {
                currentChart.remove();
                currentChart = null;
            }
            $('#tradingview-chart-container').html(''); // Clear previous chart
        }
    });

    function loadTradingViewChart(mintAddress) {
        const chartContainer = document.getElementById('tradingview-chart-container');
        if (!chartContainer) return;

        $(chartContainer).html('<p>Loading chart data...</p>');

        if (currentChart) {
            currentChart.remove(); // Remove previous chart instance
            currentChart = null;
        }

        // Fetch data for the selected token
        $.getJSON(`/api/token_data/${mintAddress}`, function(data) {
            if (data.error || data.length === 0) {
                $(chartContainer).html(`<p class="text-warning">No chart data available for ${mintAddress}.</p>`);
                return;
            }
            $(chartContainer).empty(); // Clear loading message

            currentChart = LightweightCharts.createChart(chartContainer, {
                width: chartContainer.clientWidth,
                height: 600, // Adjust as needed
                layout: {
                    backgroundColor: '#ffffff',
                    textColor: 'rgba(33, 56, 77, 1)',
                },
                grid: {
                    vertLines: { color: 'rgba(197, 203, 206, 0.5)' },
                    horzLines: { color: 'rgba(197, 203, 206, 0.5)' },
                },
                crosshair: { mode: LightweightCharts.CrosshairMode.Normal },
                rightPriceScale: { borderColor: 'rgba(197, 203, 206, 0.8)' },
                timeScale: { borderColor: 'rgba(197, 203, 206, 0.8)', timeVisible: true, secondsVisible: false },
            });

            const candleSeries = currentChart.addCandlestickSeries({
                upColor: 'rgba(0, 150, 136, 1)', // Green
                downColor: 'rgba(255, 82, 82, 1)', // Red
                borderDownColor: 'rgba(255, 82, 82, 1)',
                borderUpColor: 'rgba(0, 150, 136, 1)',
                wickDownColor: 'rgba(255, 82, 82, 1)',
                wickUpColor: 'rgba(0, 150, 136, 1)',
            });
            candleSeries.setData(data); // Data should be in {time, open, high, low, close} format

            // Optional: Add Volume Series
            const volumeData = data.map(d => ({ time: d.time, value: d.volume, color: d.open < d.close ? 'rgba(0, 150, 136, 0.5)' : 'rgba(255, 82, 82, 0.5)' }));
            const volumeSeries = currentChart.addHistogramSeries({
                priceFormat: { type: 'volume' },
                priceScaleId: '', // Overlay on main chart or use separate scale
                scaleMargins: { top: 0.8, bottom: 0 },
            });
            volumeSeries.setData(volumeData);

            currentChart.timeScale().fitContent();

        }).fail(function() {
            $(chartContainer).html(`<p class="text-danger">Failed to load chart data for ${mintAddress}.</p>`);
        });
    }


    // --- Footer Log and Time Update ---
    function updateLogs() {
        $.getJSON('/api/logs?lines=50', function(data) { // Request last 50 lines
            if(data.logs) {
                logDisplay.text(data.logs);
                logDisplay.scrollTop(logDisplay[0].scrollHeight); // Scroll to bottom
            }
        }).fail(function() {
            logDisplay.text('Failed to load logs.');
        });
    }

    function updateTime() {
        const now = new Date();
        $('#current-year').text(now.getFullYear());
        $('#current-time').text(now.toLocaleTimeString());
    }

    // --- Navigation Handling ---
    $('.nav-link').on('click', function(e) {
        e.preventDefault();
        const page = $(this).data('page');
        if (page) {
            // Update active class
            $('.nav-link').removeClass('active');
            $(this).addClass('active');
            // Load page content
            loadPage(page);
        }
    });

    // --- Initializations ---
    loadPage('dashboard'); // Load default page
    updateLogs(); // Initial log load
    logInterval = setInterval(updateLogs, 10000); // Refresh logs every 10 seconds
    updateTime();
    setInterval(updateTime, 1000); // Update time every second

    // Cleanup intervals on page unload (though with SPA, this is less of an issue)
    $(window).on('beforeunload', function() {
        if (logInterval) clearInterval(logInterval);
        if (statusInterval) clearInterval(statusInterval);
    });
});