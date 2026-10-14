// MCU Inventory System - Interactive Workspace Logic
document.addEventListener('DOMContentLoaded', () => {
    // 1. Interactive Pinout Viewer Click Handler
    const pinRows = document.querySelectorAll('.pin-row');
    const chipPinInfo = document.getElementById('chipPinInfo');

    pinRows.forEach(pin => {
        pin.addEventListener('click', () => {
            const pinNum = pin.dataset.pin;
            const pinType = pin.dataset.type ? pin.dataset.type.toUpperCase() : 'GPIO';
            const pinMeta = pin.querySelector('.pin-meta') ? pin.querySelector('.pin-meta').textContent : '';

            // Highlight selected pin
            pinRows.forEach(p => p.classList.remove('selected-pin'));
            pin.classList.add('selected-pin');

            if (chipPinInfo) {
                chipPinInfo.innerHTML = `<strong>Пін ${pinNum}:</strong> ${pinMeta}<br><span style="opacity: 0.8; font-size: 10px;">Тип: ${pinType}</span>`;
            }
        });
    });

    // 2. Interactive Build Readiness Calculator (Demo)
    const chipBtns = document.querySelectorAll('.chip-btn');
    const bomRows = document.querySelectorAll('.bom-row');
    const calcStatusPill = document.getElementById('calcStatusPill');

    chipBtns.forEach(btn => {
        btn.addEventListener('click', () => {
            chipBtns.forEach(b => b.classList.remove('active'));
            btn.classList.add('active');

            const multiplier = parseInt(btn.dataset.multiplier, 10) || 1;
            let hasDeficit = false;

            bomRows.forEach(row => {
                const base = parseInt(row.dataset.base, 10) || 1;
                const stock = parseInt(row.dataset.stock, 10) || 0;
                const req = base * multiplier;

                const reqEl = row.querySelector('.bom-req');
                const statusEl = row.querySelector('.status-badge-ok, .status-badge-deficit');

                if (reqEl) reqEl.textContent = `${req} шт`;

                if (req > stock) {
                    hasDeficit = true;
                    if (statusEl) {
                        statusEl.className = 'status-badge-deficit';
                        statusEl.textContent = `Дефіцит: -${req - stock} шт`;
                    }
                } else {
                    if (statusEl) {
                        statusEl.className = 'status-badge-ok';
                        statusEl.textContent = 'В наявності';
                    }
                }
            });

            if (calcStatusPill) {
                if (hasDeficit) {
                    calcStatusPill.className = 'chip-pill chip-rose';
                    calcStatusPill.textContent = 'Дефіцит деталей';
                    calcStatusPill.style.background = 'rgba(244, 63, 94, 0.15)';
                    calcStatusPill.style.color = 'var(--accent-rose)';
                } else {
                    calcStatusPill.className = 'chip-pill chip-emerald';
                    calcStatusPill.textContent = 'Готовий до збірки';
                    calcStatusPill.style.background = 'rgba(16, 185, 129, 0.15)';
                    calcStatusPill.style.color = 'var(--accent-emerald)';
                }
            }
        });
    });

    // 3. Ctrl+K Search Shortcut & Enter Search Navigation
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

    // 4. Auto-dismiss alerts
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
