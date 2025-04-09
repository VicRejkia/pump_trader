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
    }
});