/**
 * Interactive POS cart logic for Restaurant & Dining
 */
document.addEventListener('DOMContentLoaded', () => {
    let cart = [];
    const taxRate = parseFloat(document.getElementById('posTaxRate')?.value || '5.00');

    const cartContainer = document.getElementById('cartItemsList');
    const subtotalEl = document.getElementById('posSubtotal');
    const taxEl = document.getElementById('posTax');
    const grandTotalEl = document.getElementById('posGrandTotal');
    const cartHiddenInput = document.getElementById('cart_items_json');
    const orderTypeSelect = document.getElementById('order_type');
    const tableSelectGroup = document.getElementById('tableSelectGroup');
    const staySelectGroup = document.getElementById('staySelectGroup');
    const paymentActionSelect = document.getElementById('payment_action');

    // 1. Category Filtering
    const categoryBtns = document.querySelectorAll('.cat-filter-btn');
    const menuItems = document.querySelectorAll('.pos-menu-item');

    categoryBtns.forEach(btn => {
        btn.addEventListener('click', () => {
            categoryBtns.forEach(b => b.classList.remove('active', 'btn-3d-primary'));
            categoryBtns.forEach(b => b.classList.add('btn-3d-secondary'));
            btn.classList.add('active', 'btn-3d-primary');
            btn.classList.remove('btn-3d-secondary');

            const catId = btn.dataset.catId;
            menuItems.forEach(item => {
                if (catId === 'all' || item.dataset.catId === catId) {
                    item.style.display = 'block';
                } else {
                    item.style.display = 'none';
                }
            });
        });
    });

    // 2. Add to Cart Click
    document.querySelectorAll('.add-to-cart-btn').forEach(btn => {
        btn.addEventListener('click', (e) => {
            const card = btn.closest('.pos-menu-item');
            const id = parseInt(card.dataset.id);
            const name = card.dataset.name;
            const price = parseFloat(card.dataset.price);

            const existing = cart.find(i => i.id === id);
            if (existing) {
                existing.quantity += 1;
            } else {
                cart.push({ id, name, price, quantity: 1, notes: '' });
            }
            renderCart();
        });
    });

    // 3. Render Cart
    function renderCart() {
        if (!cartContainer) return;
        cartContainer.innerHTML = '';

        if (cart.length === 0) {
            cartContainer.innerHTML = `
                <div class="text-center text-muted py-5">
                    <i class="bi bi-cart3 fs-1 d-block mb-2 text-muted"></i>
                    <span>Your order cart is empty. Click dishes from menu to add.</span>
                </div>
            `;
            updateTotals();
            return;
        }

        cart.forEach((item, index) => {
            const itemTotal = (item.price * item.quantity).toFixed(2);
            const row = document.createElement('div');
            row.className = 'd-flex align-items-center justify-content-between p-2 mb-2 bg-light rounded-3 border';
            row.innerHTML = `
                <div class="flex-grow-1 me-2">
                    <div class="fw-bold fs-6 text-dark">${item.name}</div>
                    <div class="small text-muted">₹${item.price.toFixed(2)} each</div>
                </div>
                <div class="d-flex align-items-center gap-2">
                    <button type="button" class="btn btn-sm btn-outline-secondary px-2 py-0 dec-btn" data-index="${index}">-</button>
                    <span class="fw-bold font-mono">${item.quantity}</span>
                    <button type="button" class="btn btn-sm btn-outline-secondary px-2 py-0 inc-btn" data-index="${index}">+</button>
                    <div class="fw-bold font-mono ms-2 text-primary" style="min-width: 65px; text-align: right;">₹${itemTotal}</div>
                    <button type="button" class="btn btn-sm text-danger remove-btn ms-1" data-index="${index}"><i class="bi bi-trash"></i></button>
                </div>
            `;
            cartContainer.appendChild(row);
        });

        // Add event listeners
        cartContainer.querySelectorAll('.inc-btn').forEach(b => {
            b.addEventListener('click', (e) => {
                const idx = parseInt(e.target.dataset.index);
                cart[idx].quantity += 1;
                renderCart();
            });
        });

        cartContainer.querySelectorAll('.dec-btn').forEach(b => {
            b.addEventListener('click', (e) => {
                const idx = parseInt(e.target.dataset.index);
                if (cart[idx].quantity > 1) {
                    cart[idx].quantity -= 1;
                } else {
                    cart.splice(idx, 1);
                }
                renderCart();
            });
        });

        cartContainer.querySelectorAll('.remove-btn').forEach(b => {
            b.addEventListener('click', (e) => {
                const idx = parseInt(b.closest('.remove-btn').dataset.index);
                cart.splice(idx, 1);
                renderCart();
            });
        });

        updateTotals();
    }

    function updateTotals() {
        let subtotal = 0;
        cart.forEach(i => subtotal += (i.price * i.quantity));
        const tax = (subtotal * (taxRate / 100));
        const grandTotal = subtotal + tax;

        if (subtotalEl) subtotalEl.textContent = `₹ ${subtotal.toFixed(2)}`;
        if (taxEl) taxEl.textContent = `₹ ${tax.toFixed(2)}`;
        if (grandTotalEl) grandTotalEl.textContent = `₹ ${grandTotal.toFixed(2)}`;
        if (cartHiddenInput) cartHiddenInput.value = JSON.stringify(cart);
    }

    // 4. Dynamic Order Type UI handling
    if (orderTypeSelect) {
        orderTypeSelect.addEventListener('change', () => {
            if (orderTypeSelect.value === 'Room-Service') {
                if (staySelectGroup) staySelectGroup.style.display = 'block';
                if (paymentActionSelect) paymentActionSelect.value = 'PostToRoom';
            } else if (orderTypeSelect.value === 'Takeaway') {
                if (tableSelectGroup) tableSelectGroup.style.display = 'none';
                if (staySelectGroup) staySelectGroup.style.display = 'none';
            } else {
                if (tableSelectGroup) tableSelectGroup.style.display = 'block';
                if (staySelectGroup) staySelectGroup.style.display = 'none';
            }
        });
    }

    // Initialize Empty
    renderCart();
});
