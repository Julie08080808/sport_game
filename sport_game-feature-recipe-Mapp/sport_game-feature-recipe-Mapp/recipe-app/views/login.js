// 登入 / 註冊頁邏輯
let currentMode = 'login';

function switchTab(mode) {
    currentMode = mode;
    document.getElementById('tab-login').classList.toggle('active', mode === 'login');
    document.getElementById('tab-register').classList.toggle('active', mode === 'register');
    document.getElementById('submit-btn').textContent = mode === 'login' ? '登入' : '註冊';
    document.getElementById('auth-msg').textContent = '';
}

async function submitAuth() {
    const username = document.getElementById('username').value.trim();
    const password = document.getElementById('password').value.trim();
    const msg = document.getElementById('auth-msg');

    if (!username || !password) {
        msg.className = 'auth-msg error';
        msg.textContent = '請輸入帳號與密碼';
        return;
    }

    try {
        const res = await fetch(`/api/users/${currentMode}`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ username, password })
        });
        const data = await res.json();

        if (!res.ok) {
            msg.className = 'auth-msg error';
            msg.textContent = data.detail || '操作失敗';
            return;
        }

        if (currentMode === 'login') {
            sessionStorage.setItem('username', data.user.username);
            sessionStorage.setItem('userId', data.user.id);
            msg.className = 'auth-msg success';
            msg.textContent = '登入成功!跳轉中...';
            setTimeout(() => { window.location.href = '/'; }, 800);
        } else {
            msg.className = 'auth-msg success';
            msg.textContent = '註冊成功!請點上方「登入」分頁登入';
            switchTab('login');
        }
    } catch (err) {
        msg.className = 'auth-msg error';
        msg.textContent = '伺服器無回應,請確認後端是否啟動';
    }
}

// Enter 鍵送出
document.addEventListener('keydown', (e) => {
    if (e.key === 'Enter') submitAuth();
});
