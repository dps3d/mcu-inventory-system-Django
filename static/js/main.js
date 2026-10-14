// MCU Inventory System - Core Client Workspace Logic
document.addEventListener('DOMContentLoaded', () => {
    // 1. Global Search Shortcut (Ctrl+K or Cmd+K) & Enter Navigation
    const searchInput = document.getElementById('globalSearchInput');
    document.addEventListener('keydown', (e) => {
        if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === 'k') {
            e.preventDefault();
            if (searchInput) {
                searchInput.focus();
                searchInput.select();
            }
        }
    });

    if (searchInput) {
        searchInput.addEventListener('keydown', (e) => {
            if (e.key === 'Enter') {
                e.preventDefault();
                const q = searchInput.value.trim();
                window.location.href = `/catalog/${q ? '?q=' + encodeURIComponent(q) : ''}`;
            }
        });
    }

    // 2. Auto-dismiss flash message toasts
    const toasts = document.querySelectorAll('.toast-message');
    toasts.forEach(toast => {
        setTimeout(() => {
            toast.style.transition = 'opacity 0.3s ease, transform 0.3s ease';
            toast.style.opacity = '0';
            toast.style.transform = 'translateY(-6px)';
            setTimeout(() => toast.remove(), 300);
        }, 5000);
    });
});
