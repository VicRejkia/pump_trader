// Removed redundant log fetching logic. It's now handled in base.html
document.addEventListener('DOMContentLoaded', () => {
    // Get sidebar elements
    const sidebar = document.querySelector('.sidebar');
    const sidebarToggle = document.querySelector('.sidebar-toggle');
    const mainContent = document.querySelector('.main-content');
    
    // Function to toggle sidebar
    function toggleSidebar() {
        sidebar.classList.toggle('collapsed');
        mainContent.classList.toggle('expanded');
        
        // Store the sidebar state in localStorage
        const isCollapsed = sidebar.classList.contains('collapsed');
        localStorage.setItem('sidebarCollapsed', isCollapsed);
    }
    
    // Add click event to sidebar toggle button
    sidebarToggle.addEventListener('click', toggleSidebar);
    
    // Check localStorage for saved sidebar state
    const savedState = localStorage.getItem('sidebarCollapsed');
    if (savedState === 'true') {
        sidebar.classList.add('collapsed');
        mainContent.classList.add('expanded');
    }
    
    // Handle active menu items
    const currentPath = window.location.pathname;
    const menuItems = document.querySelectorAll('.sidebar-menu a');
    
    menuItems.forEach(item => {
        // Get the path from the href attribute
        const itemPath = item.getAttribute('href');
        
        // Check if the current path matches the menu item path
        // or if we're at root and this is the charts link
        if (itemPath === currentPath || 
            (currentPath === '/' && itemPath === '/charts')) {
            item.classList.add('active');
        }
    });
    
    // For mobile: close sidebar when clicking outside on small screens
    if (window.innerWidth <= 768) {
        document.addEventListener('click', (e) => {
            // If click is outside sidebar and sidebar is expanded
            if (!sidebar.contains(e.target) && 
                !sidebarToggle.contains(e.target) && 
                sidebar.classList.contains('expanded')) {
                sidebar.classList.remove('expanded');
            }
        });
        
        // Toggle expanded class for mobile view
        sidebarToggle.addEventListener('click', () => {
            sidebar.classList.toggle('expanded');
        });
        
        // Add token filtering functionality
        document.addEventListener('DOMContentLoaded', () => {
            const applyFiltersBtn = document.getElementById('apply-filters-btn');
            const tokenListContainer = document.getElementById('token-list-container');
        
            applyFiltersBtn.addEventListener('click', async () => {
                const maxSocials = document.getElementById('filter-max-socials').value;
                const maxRugcheck = document.getElementById('filter-max-rugcheck').value;
                const minVolume = document.getElementById('filter-min-volume').value;
                const timeWindow = document.getElementById('filter-time-window').value;
                const portfolioOnly = document.getElementById('filter-portfolio-only').checked;
                const volumeAggregation = document.getElementById('filter-volume-aggregation').value;
        
                const params = new URLSearchParams({
                    max_socials: maxSocials,
                    max_rugcheck: maxRugcheck,
                    min_volume: minVolume,
                    time_window: timeWindow,
                    portfolio_only: portfolioOnly,
                    volume_aggregation: volumeAggregation
                }).toString();
        
                try {
                    const response = await fetch(`/api/filtered_tokens?${params}`);
                    if (!response.ok) {
                        throw new Error(`HTTP error! status: ${response.status}`);
                    }
                    const tokens = await response.json();
        
                    // Clear existing token list
                    tokenListContainer.innerHTML = '';
        
                    if (tokens.length === 0) {
                        tokenListContainer.innerHTML = '<div class="list-group-item">No tokens found with the selected filters.</div>';
                    } else {
                        tokens.forEach(token => {
                            const listItem = document.createElement('div');
                            listItem.classList.add('list-group-item');
                            listItem.textContent = `${token.name} (${token.symbol}) - ${token.mint} - Volume: ${token.volume}`;
                            listItem.addEventListener('click', () => {
                                navigator.clipboard.writeText(token.mint).then(() => {
                                    alert('Mint copied to clipboard!');
                                });
                            });
                            tokenListContainer.appendChild(listItem);
                        });
                    }
                } catch (error) {
                    console.error('Failed to fetch filtered tokens:', error);
                    tokenListContainer.innerHTML = '<div class="list-group-item">Failed to load tokens. Please check the console for errors.</div>';
                }
            });
        });
    }

    // --- Bot Control Logic ---
    const startButton = document.getElementById('start-bot-btn');
    const stopButton = document.getElementById('stop-bot-btn');
    let statusCheckInterval; // Variable to hold the interval ID

    // Function to update button visibility based on status
    function updateButtonStates(status) {
        console.log("Updating button states based on status:", status);
        switch (status) {
            case "RUNNING":
                startButton.style.display = 'none';
                stopButton.style.display = 'inline-block';
                startButton.disabled = true; // Disable start when running
                stopButton.disabled = false; // Enable stop when running
                break;
            case "STARTING":
                startButton.style.display = 'inline-block'; // Show start but disable
                stopButton.style.display = 'none';
                startButton.disabled = true;
                stopButton.disabled = true; // Disable stop while starting
                // Optionally update button text: startButton.textContent = 'Starting...';
                break;
            case "STOPPING":
                startButton.style.display = 'none';
                stopButton.style.display = 'inline-block'; // Show stop but disable
                startButton.disabled = true; // Disable start while stopping
                stopButton.disabled = true;
                // Optionally update button text: stopButton.textContent = 'Stopping...';
                break;
            case "STOPPED":
            case "ERROR": // Treat ERROR as STOPPED for button state
            default: // Default to stopped state
                startButton.style.display = 'inline-block';
                stopButton.style.display = 'none';
                startButton.disabled = false; // Enable start when stopped
                stopButton.disabled = true; // Disable stop when stopped
                // Reset button text if changed: startButton.textContent = 'Start Bot';
                break;
        }
    }

    // Function to fetch bot status
    async function checkBotStatus() {
        try {
            const response = await fetch('/api/bot_status');
            if (!response.ok) {
                console.error('Error fetching bot status:', response.statusText);
                updateButtonStates("ERROR"); // Assume error means stopped for UI
                return;
            }
            const data = await response.json();
            updateButtonStates(data.status);
        } catch (error) {
            console.error('Network error fetching bot status:', error);
            updateButtonStates("ERROR"); // Assume error means stopped for UI
        }
    }

    if (startButton && stopButton) {
        // Event listener for Start Button
        startButton.addEventListener('click', async () => {
            console.log('Start Bot button clicked - sending command');
            updateButtonStates("STARTING"); // Immediately reflect intent

            try {
                const response = await fetch('/start_bot', { method: 'POST' });
                const result = await response.json();
                console.log('Start Bot command response:', result);
                // No need to update buttons here, periodic check will handle it
                if (!response.ok) {
                    console.error("Start command failed:", result);
                    checkBotStatus(); // Re-check status immediately on failure
                }
            } catch (error) {
                console.error('Error sending start command:', error);
                checkBotStatus(); // Re-check status immediately on failure
            }
        });

        // Event listener for Stop Button
        stopButton.addEventListener('click', async () => {
            console.log('Stop Bot button clicked - sending command');
            updateButtonStates("STOPPING"); // Immediately reflect intent

            try {
                const response = await fetch('/stop_bot', { method: 'POST' });
                const result = await response.json();
                console.log('Stop Bot command response:', result);
                // No need to update buttons here, periodic check will handle it
                 if (!response.ok) {
                    console.error("Stop command failed:", result);
                    checkBotStatus(); // Re-check status immediately on failure
                }
            } catch (error) {
                console.error('Error sending stop command:', error);
                 checkBotStatus(); // Re-check status immediately on failure
            }
        });

        // Initial status check on page load
        checkBotStatus();

        // Periodically check status
        statusCheckInterval = setInterval(checkBotStatus, 5000); // Check every 5 seconds

    } else {
        console.warn('Start or Stop button not found in the DOM.');
    }
    // --- End Bot Control Logic ---

});