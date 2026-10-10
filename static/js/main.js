/**
 * Main Client Scripts for Hotel & Restaurant Management System
 */
document.addEventListener('DOMContentLoaded', () => {
    // 1. Initialize Bootstrap Tooltips & Popovers
    const tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'));
    tooltipTriggerList.map(el => new bootstrap.Tooltip(el));

    // 2. Mobile Sidebar Toggle & Backdrop
    const sidebarToggleBtn = document.getElementById('sidebarToggle');
    const sidebarCloseBtn = document.getElementById('sidebarCloseBtn');
    const sidebarBackdrop = document.getElementById('sidebarBackdrop');
    const sidebar = document.querySelector('.app-sidebar');

    function openSidebar() {
        if (sidebar) sidebar.classList.add('show');
        if (sidebarBackdrop) sidebarBackdrop.classList.add('show');
        document.body.style.overflow = 'hidden';
    }

    function closeSidebar() {
        if (sidebar) sidebar.classList.remove('show');
        if (sidebarBackdrop) sidebarBackdrop.classList.remove('show');
        document.body.style.overflow = '';
    }

    if (sidebarToggleBtn) {
        sidebarToggleBtn.addEventListener('click', (e) => {
            e.stopPropagation();
            if (sidebar && sidebar.classList.contains('show')) {
                closeSidebar();
            } else {
                openSidebar();
            }
        });
    }

    if (sidebarCloseBtn) {
        sidebarCloseBtn.addEventListener('click', closeSidebar);
    }

    if (sidebarBackdrop) {
        sidebarBackdrop.addEventListener('click', closeSidebar);
    }

    // 3. Dynamic Room Availability in Booking Form
    const checkinInput = document.getElementById('checkin_date');
    const checkoutInput = document.getElementById('checkout_date');
    const categorySelect = document.getElementById('room_category_id');
    const roomsSelect = document.getElementById('allocated_rooms');
    const agreedRateInput = document.getElementById('agreed_rate_per_night');

    async function updateAvailableRooms() {
        if (!checkinInput || !checkoutInput || !categorySelect || !roomsSelect) return;
        const cin = checkinInput.value;
        const cout = checkoutInput.value;
        const catId = categorySelect.value;

        if (!cin || !cout) return;

        try {
            const resp = await fetch(`/bookings/api/available-rooms?checkin=${cin}&checkout=${cout}&category_id=${catId}`);
            if (resp.ok) {
                const rooms = await resp.json();
                roomsSelect.innerHTML = '';
                if (rooms.length === 0) {
                    const opt = document.createElement('option');
                    opt.disabled = true;
                    opt.textContent = 'No available rooms for this date range';
                    roomsSelect.appendChild(opt);
                } else {
                    rooms.forEach(r => {
                        const opt = document.createElement('option');
                        opt.value = r.id;
                        opt.textContent = `Room ${r.room_number} (${r.category} - ${r.floor})`;
                        opt.selected = true; // Select by default if matching
                        roomsSelect.appendChild(opt);
                    });
                }
            }
        } catch (err) {
            console.error('Error fetching available rooms:', err);
        }
    }

    if (checkinInput && checkoutInput && categorySelect) {
        checkinInput.addEventListener('change', updateAvailableRooms);
        checkoutInput.addEventListener('change', updateAvailableRooms);
        categorySelect.addEventListener('change', updateAvailableRooms);
    }
});
