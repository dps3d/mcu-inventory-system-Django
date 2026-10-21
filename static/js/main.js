// MCU Inventory System - Core Client Workspace Logic

// 1. Mobile Sidebar Drawer Logic
if (typeof window.__lastSidebarToggle === 'undefined') {
    window.__lastSidebarToggle = 0;
}

function openMobileSidebar() {
    const sidebar = document.querySelector('#appSidebar');
    const backdrop = document.querySelector('#sidebarBackdrop');
    const toggleBtn = document.querySelector('#mobileMenuToggle');
    if (!sidebar) return;

    sidebar.classList.add('is-open');
    if (backdrop) backdrop.classList.add('is-active');
    document.body.classList.add('sidebar-locked');
    if (toggleBtn) toggleBtn.setAttribute('aria-expanded', 'true');
}

function closeMobileSidebar() {
    const sidebar = document.querySelector('#appSidebar');
    const backdrop = document.querySelector('#sidebarBackdrop');
    const toggleBtn = document.querySelector('#mobileMenuToggle');
    if (!sidebar) return;

    sidebar.classList.remove('is-open');
    if (backdrop) backdrop.classList.remove('is-active');
    document.body.classList.remove('sidebar-locked');
    if (toggleBtn) toggleBtn.setAttribute('aria-expanded', 'false');
}

function toggleMobileSidebar(e) {
    if (e) {
        if (typeof e.preventDefault === 'function') e.preventDefault();
        if (typeof e.stopPropagation === 'function') e.stopPropagation();
    }
    const now = Date.now();
    if (window.__lastSidebarToggle && (now - window.__lastSidebarToggle < 280)) {
        return; // Guard against duplicate calls
    }
    window.__lastSidebarToggle = now;

    const sidebar = document.querySelector('#appSidebar');
    if (!sidebar) return;

    if (sidebar.classList.contains('is-open')) {
        closeMobileSidebar();
    } else {
        openMobileSidebar();
    }
}

window.openMobileSidebar = openMobileSidebar;
window.closeMobileSidebar = closeMobileSidebar;
window.toggleMobileSidebar = toggleMobileSidebar;

function initApp() {
    const mobileMenuToggle = document.querySelector('#mobileMenuToggle');
    const sidebarCloseBtn = document.querySelector('#sidebarCloseBtn');
    const sidebarBackdrop = document.querySelector('#sidebarBackdrop');
    const sidebar = document.querySelector('#appSidebar');

    if (mobileMenuToggle && !mobileMenuToggle._bound) {
        mobileMenuToggle._bound = true;
        if (!mobileMenuToggle.hasAttribute('onclick')) {
            mobileMenuToggle.addEventListener('click', toggleMobileSidebar);
        }
    }

    if (sidebarCloseBtn && !sidebarCloseBtn._bound) {
        sidebarCloseBtn._bound = true;
        sidebarCloseBtn.addEventListener('click', (e) => {
            if (e) { e.preventDefault(); e.stopPropagation(); }
            closeMobileSidebar();
        });
    }

    if (sidebarBackdrop && !sidebarBackdrop._bound) {
        sidebarBackdrop._bound = true;
        sidebarBackdrop.addEventListener('click', (e) => {
            if (e) { e.preventDefault(); e.stopPropagation(); }
            closeMobileSidebar();
        });
    }

    // Close drawer on Escape key
    document.addEventListener('keydown', (e) => {
        if (e.key === 'Escape' && sidebar && sidebar.classList.contains('is-open')) {
            closeMobileSidebar();
        }
    });

    // Close drawer on navigation click on small screens
    if (sidebar && !sidebar._navBound) {
        sidebar._navBound = true;
        const navLinks = sidebar.querySelectorAll('.nav-item, .admin-top-btn, .btn-action');
        navLinks.forEach(link => {
            link.addEventListener('click', () => {
                if (window.innerWidth <= 1024 && sidebar.classList.contains('is-open')) {
                    closeMobileSidebar();
                }
            });
        });
    }

    // Handle browser bfcache navigation back - close drawer cleanly
    window.addEventListener('pageshow', () => {
        closeMobileSidebar();
    });

    // 2. Global Search Shortcut (Ctrl+K or Cmd+K) & Enter Navigation
    const searchInput = document.querySelector('#globalSearchInput');
    document.addEventListener('keydown', (e) => {
        if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === 'k') {
            e.preventDefault();
            if (searchInput) {
                searchInput.focus();
                searchInput.select();
            }
        }
    });

    if (searchInput && !searchInput._bound) {
        searchInput._bound = true;
        searchInput.addEventListener('keydown', (e) => {
            if (e.key === 'Enter') {
                e.preventDefault();
                const q = searchInput.value.trim();
                window.location.href = `/catalog/${q ? '?q=' + encodeURIComponent(q) : ''}`;
            }
        });
    }

    // 3. Auto-dismiss flash message toasts
    const toasts = document.querySelectorAll('.toast-message');
    toasts.forEach(toast => {
        setTimeout(() => {
            toast.style.transition = 'opacity 0.3s ease, transform 0.3s ease';
            toast.style.opacity = '0';
            toast.style.transform = 'translateY(-6px)';
            setTimeout(() => toast.remove(), 300);
        }, 5000);
    });
}

// Ensure execution even if DOMContentLoaded has already fired
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', initApp);
} else {
    initApp();
}
