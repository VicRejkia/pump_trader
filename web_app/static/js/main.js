$(document).ready(function() {
    const mainContentArea = $('#dynamic-content-placeholder');
    const pageTitle = $('#page-title');
    const logDisplay = $('#log-display');
    let logInterval;
    let statusInterval;
    let currentChart = null;

    function loadPage(pageName) {
        console.log(`Loading page: ${pageName}`);
        
        // Clear any existing intervals and the chart when changing pages
        if (statusInterval) clearInterval(statusInterval);
        if (currentChart) {
            currentChart.remove();
            currentChart = null;
        }

        mainContentArea.html('<p class="text-info">Loading...</p>');
        mainContentArea.load(`/page/${pageName}`, function(response, status, xhr) {
            if (status === "error") {
                mainContentArea.html(`<p class="text-danger">Error loading page: ${xhr.status} ${xhr.statusText}</p>`);
                return;
            }
            
            pageTitle.text(pageName.charAt(0).toUpperCase() + pageName.slice(1));
            
            // Activate functions specific to the newly loaded page content
            if (pageName === 'dashboard') {
                loadDashboardData();
                statusInterval = setInterval(loadDashboardData, 5000);
            } else if (pageName === 'config') {
                loadConfigData();
            } else if (pageName === 'charts') {
                initializeChartsPage();
            }
        });
    }

    // --- Dashboard Functions (Corrected) ---
    function loadDashboardData() {
        $.getJSON('/api/status', function(data) {
            if (data.error) {
                console.error("Error fetching bot status:", data.error);
                $('#bot-file-status').text('Error');
                $('#bot-uptime, #bot-asyncio-tasks, #bot-sol-balance, #bot-token-subscriptions').text('Error');
                return;
            }
            
            const uptimeSeconds = data.uptime_seconds || 0;
            const hours = Math.floor(uptimeSeconds / 3600);
            const minutes = Math.floor((uptimeSeconds % 3600) / 60);
            const seconds = uptimeSeconds % 60;
            const uptimeFormatted = `${hours}h ${minutes}m ${seconds}s`;

            $('#bot-file-status').text(data.bot_process_status || 'N/A');
            $('#bot-uptime').text(uptimeFormatted);
            $('#bot-asyncio-tasks').text(data.asyncio_tasks_count !== undefined ? data.asyncio_tasks_count : 'N/A');
            $('#bot-sol-balance').text(data.current_sol_balance !== undefined ? parseFloat(data.current_sol_balance).toFixed(4) : 'N/A');
            $('#bot-token-subscriptions').text(data.active_token_subscriptions_count !== undefined ? data.active_token_subscriptions_count : 'N/A');
            
        }).fail(function() {
            $('#bot-file-status').text('Error loading status');
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
            const sortedKeys = Object.keys(config).sort(); // Sort keys for consistent order
            sortedKeys.forEach(key => {
                const value = config[key];
                let inputType = 'text';
                if (typeof value === 'boolean') inputType = 'checkbox';
                else if (typeof value === 'number') inputType = 'number';

                formHtml += `<div class="form-group row mb-2">
                                <label for="config-${key}" class="col-sm-4 col-form-label">${key.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase())}</label>
                                <div class="col-sm-8">`;
                if (inputType === 'checkbox') {
                    formHtml += `<input type="checkbox" class="form-check-input" id="config-${key}" name="${key}" ${value ? 'checked' : ''}>`;
                } else if (Array.isArray(value)) {
                    formHtml += `<textarea class="form-control" id="config-${key}" name="${key}" rows="2">${JSON.stringify(value, null, 2)}</textarea>`;
                    formHtml += `<small class="form-text text-muted">Enter as a valid JSON list.</small>`;
                } else {
                    formHtml += `<input type="${inputType}" class="form-control" id="config-${key}" name="${key}" value="${value}">`;
                }
                formHtml += `</div></div>`;
            });
            container.html(formHtml);
        }).fail(function() {
            container.html('<p class="text-danger">Failed to load configuration.</p>');
        });
    }
    
    // --- Charts Page Specific Functions ---
    function initializeChartsPage() {
        const tokenSelect = $('#token-select');
        if (tokenSelect.length === 0) return;

        tokenSelect.html('<option value="">Loading tokens...</option>');
        $.getJSON('/api/tokens')
            .done(function(tokens) {
                if (!tokens || tokens.length === 0) {
                    tokenSelect.html('<option value="">No tokens found in database</option>');
                    return;
                }
                tokenSelect.empty().append('<option value="" selected disabled>Select a token to view</option>');
                tokens.sort((a, b) => (a.name || a.mint).localeCompare(b.name || b.mint));
                tokens.forEach(function(token) {
                    const displayName = token.name && token.name !== token.mint ? `${token.name} (${token.symbol || 'N/A'}) - ${token.mint}` : token.mint;
                    tokenSelect.append($('<option>', { value: token.mint, text: displayName }));
                });
            })
            .fail(function() {
                tokenSelect.html('<option value="">Failed to load tokens</option>');
            });
    }

    function loadTradingViewChart(mintAddress) {
        const chartContainer = document.getElementById('tradingview-chart-container');
        if (!chartContainer) return;

        $(chartContainer).html('<p class="text-info mt-3">Loading chart data...</p>');
        if (currentChart) currentChart.remove();

        $.getJSON(`/api/token_data/${mintAddress}`)
            .done(function(data) {
                if (data.error || data.length === 0) {
                    $(chartContainer).html(`<p class="text-warning mt-3">${data.error || 'No chart data available for this token.'}</p>`);
                    return;
                }
                $(chartContainer).empty();

                currentChart = LightweightCharts.createChart(chartContainer, {
                    width: chartContainer.clientWidth,
                    height: 600,
                    layout: { backgroundColor: '#ffffff', textColor: '#333' },
                    grid: { vertLines: { color: '#f0f0f0' }, horzLines: { color: '#f0f0f0' } },
                    crosshair: { mode: LightweightCharts.CrosshairMode.Normal },
                    timeScale: { timeVisible: true, secondsVisible: true }
                });

                const candleSeries = currentChart.addCandlestickSeries({
                    upColor: 'rgba(0, 150, 136, 1)', downColor: 'rgba(255, 82, 82, 1)',
                    borderDownColor: 'rgba(255, 82, 82, 1)', borderUpColor: 'rgba(0, 150, 136, 1)',
                    wickDownColor: 'rgba(255, 82, 82, 1)', wickUpColor: 'rgba(0, 150, 136, 1)',
                });
                candleSeries.setData(data);

                const volumeData = data.map(d => ({ time: d.time, value: d.volume, color: d.open < d.close ? 'rgba(0, 150, 136, 0.5)' : 'rgba(255, 82, 82, 0.5)' }));
                const volumeSeries = currentChart.addHistogramSeries({
                    priceFormat: { type: 'volume' }, priceScaleId: '',
                    scaleMargins: { top: 0.8, bottom: 0 },
                });
                volumeSeries.setData(volumeData);
                currentChart.timeScale().fitContent();
            })
            .fail(function(xhr) {
                const errorMsg = xhr.responseJSON ? xhr.responseJSON.error : "Failed to load chart data.";
                $(chartContainer).html(`<p class="text-danger mt-3">${errorMsg}</p>`);
            });
    }

    // --- Global Event Handlers using Delegation ---
    // Handles config form submission
    $('body').on('submit', '#config-form', function(event) {
        event.preventDefault();
        const configUpdates = {};
        $(this).find('input, textarea').each(function() {
            const input = $(this);
            const key = input.attr('name');
            let value;
            if (input.attr('type') === 'checkbox') {
                value = input.is(':checked');
            } else if (input.is('textarea')) {
                try { value = JSON.parse(input.val()); } catch (e) { value = input.val(); }
            } else if (input.attr('type') === 'number') {
                value = parseFloat(input.val());
            } else {
                value = input.val();
            }
            configUpdates[key] = value;
        });

        $('#config-save-status').html('<div class="alert alert-info">Saving...</div>');
        $.ajax({
            url: '/api/config/update',
            method: 'POST',
            contentType: 'application/json',
            data: JSON.stringify(configUpdates),
            success: function(response) {
                $('#config-save-status').html(`<div class="alert alert-success">${response.message}</div>`);
            },
            error: function(xhr) {
                $('#config-save-status').html(`<div class="alert alert-danger">${xhr.responseJSON.error}</div>`);
            }
        });
    });

    // Handles chart token selection
    $('body').on('change', '#token-select', function() {
        const mintAddress = $(this).val();
        if (mintAddress) loadTradingViewChart(mintAddress);
    });

    // --- Navigation ---
    $('.nav-link').on('click', function(e) {
        e.preventDefault();
        const page = $(this).data('page');
        if (page) {
            $('.nav-link').removeClass('active');
            $(this).addClass('active');
            loadPage(page);
        }
    });

    // --- Initializations ---
    loadPage('dashboard');
    updateLogs();
    logInterval = setInterval(updateLogs, 10000);
    
    function updateLogs() {
        $.getJSON('/api/logs?lines=100', function(data) {
            logDisplay.text(data.logs || "Failed to load logs.");
            logDisplay.scrollTop(logDisplay[0].scrollHeight);
        });
    }

    // Cleanup intervals on unload
    $(window).on('beforeunload', () => {
        if (logInterval) clearInterval(logInterval);
        if (statusInterval) clearInterval(statusInterval);
    });
});