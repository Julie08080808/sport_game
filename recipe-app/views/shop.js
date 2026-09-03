// ==========================================
// 商店 - 前端邏輯
// ==========================================
// user_id 來源優先順序:
//   1. 網址參數 ?user_id=5 (Unity WebView 開這個頁面時會帶上)
//   2. sessionStorage 的 userId (網頁登入後)
//   3. 都沒有的話,顯示輸入框讓測試者手動輸入

const API_SHOP = "/api/shop";

let USER_ID = new URLSearchParams(window.location.search).get('user_id')
    || sessionStorage.getItem('userId')
    || null;

let shopItems = [];

function setUserId() {
    const val = document.getElementById('uid-input').value;
    if (!val) return;
    USER_ID = val;
    refreshAll();
}

function showToast(text) {
    const toast = document.getElementById('toast');
    toast.textContent = text;
    toast.classList.add('show');
    setTimeout(() => toast.classList.remove('show'), 2000);
}

async function loadMoney() {
    const moneyEl = document.getElementById('money-amount');
    if (!USER_ID) {
        moneyEl.textContent = '未登入';
        return;
    }
    try {
        const res = await fetch(`/api/users/profile/${USER_ID}`);
        const data = await res.json();
        moneyEl.textContent = data.data ? data.data.money : '--';
    } catch (err) {
        moneyEl.textContent = '--';
    }
}

async function loadItems() {
    const grid = document.getElementById('items-grid');
    try {
        const res = await fetch(`${API_SHOP}/items`);
        const data = await res.json();
        shopItems = data.items || [];

        if (shopItems.length === 0) {
            grid.innerHTML = '<p class="hint">商店目前沒有上架商品</p>';
            return;
        }

        grid.innerHTML = shopItems.map(item => `
            <div class="item-card">
                <img src="${item.icon_url || ''}" alt="${item.item_name}" onerror="this.style.visibility='hidden';">
                <div class="item-name">${item.item_name}</div>
                <div class="item-desc">${item.description || ''}</div>
                <div class="item-price">💰 ${item.price}</div>
                <button class="buy-btn" onclick="buyItem(${item.item_id})">購買</button>
            </div>
        `).join('');
    } catch (err) {
        grid.innerHTML = '<p class="hint">無法連接商店,請確認伺服器是否啟動</p>';
    }
}

async function loadInventory() {
    const grid = document.getElementById('inventory-grid');
    if (!USER_ID) {
        grid.innerHTML = '<p class="hint">請先登入或輸入 user_id 才能查看庫存</p>';
        return;
    }
    try {
        const res = await fetch(`${API_SHOP}/inventory/${USER_ID}`);
        const data = await res.json();
        const items = data.items || [];

        if (items.length === 0) {
            grid.innerHTML = '<p class="hint">尚未擁有任何商品</p>';
            return;
        }

        grid.innerHTML = items.map(item => `
            <div class="item-card owned">
                <img src="${item.icon_url || ''}" alt="${item.item_name}" onerror="this.style.visibility='hidden';">
                <div class="item-name">${item.item_name}</div>
                <div class="item-qty">持有 x${item.quantity}</div>
            </div>
        `).join('');
    } catch (err) {
        grid.innerHTML = '<p class="hint">無法載入庫存</p>';
    }
}

async function buyItem(itemId) {
    if (!USER_ID) {
        showToast('請先登入,或在上方輸入 user_id');
        document.getElementById('uid-bar').style.display = 'flex';
        return;
    }

    const form = new URLSearchParams();
    form.set('user_id', USER_ID);
    form.set('item_id', itemId);
    form.set('quantity', 1);

    try {
        const res = await fetch(`${API_SHOP}/purchase`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
            body: form
        });
        const data = await res.json();

        if (!res.ok) {
            showToast(data.detail || '購買失敗');
            return;
        }

        showToast(data.message || '購買成功');
        document.getElementById('money-amount').textContent = data.money;
        loadInventory();
    } catch (err) {
        showToast('伺服器無回應,請確認後端是否啟動');
    }
}

function refreshAll() {
    loadMoney();
    loadInventory();
}

async function init() {
    if (!USER_ID) {
        document.getElementById('uid-bar').style.display = 'flex';
    }
    await loadItems();
    refreshAll();
}

init();
