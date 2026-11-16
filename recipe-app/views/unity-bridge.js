/*
 * Unity WebView 橋接(UniWebView)
 * ------------------------------------------------------------
 * Unity 開網頁時會在網址帶 ?userId=12，這支檔案負責：
 *   1. 把 userId 存進 sessionStorage(點進小遊戲再回來也還在)
 *   2. 在 App 裡時顯示「返回遊戲」按鈕 → uniwebview://close 關掉網頁回到 Unity
 *   3. 在 App 裡時隱藏網頁版的登入列(玩家已經在 Unity 登入過)
 *   4. 提供 UnityBridge.sendResult({ score: 80 }) 把結果傳回 Unity
 *
 * 用一般瀏覽器開(網址沒有 userId)時什麼都不做，網頁版不受影響。
 * 使用方式：在 HTML 加  <script src="/static/unity-bridge.js"></script>
 */
(function () {
    // 有些手機 WebView 會擋 sessionStorage，讀寫失敗也不能讓整支程式停掉
    function storageGet(key) {
        try { return sessionStorage.getItem(key); } catch (e) { return null; }
    }
    function storageSet(key, value) {
        try { sessionStorage.setItem(key, value); } catch (e) { /* 忽略 */ }
    }

    const params = new URLSearchParams(location.search);
    const urlUserId = params.get('userId');

    if (urlUserId !== null) {
        storageSet('userId', urlUserId);
        storageSet('inUnityApp', 'true');
    }

    // 網址有 userId 就一定算在 App 裡，不只靠 sessionStorage
    const inApp = urlUserId !== null || storageGet('inUnityApp') === 'true';
    const currentUserId = urlUserId !== null ? urlUserId : storageGet('userId');

    function getUserId() {
        // -1 代表 Unity 端沒登入
        return currentUserId === null || currentUserId === '-1' ? null : Number(currentUserId);
    }

    // 站內網址都帶上 userId，換頁後也知道自己在 App 裡
    function withUserId(href) {
        if (currentUserId === null) return href;
        try {
            const u = new URL(href, location.href);
            if (u.origin !== location.origin) return href;
            u.searchParams.set('userId', currentUserId);
            return u.toString();
        } catch (e) {
            return href;
        }
    }

    function closeWebView() {
        if (inApp) {
            location.href = 'uniwebview://close';
        }
    }

    // data 例：{ game: 'memory-match', score: 80 } → uniwebview://result?game=memory-match&score=80
    function sendResult(data) {
        if (!inApp) return;
        const query = new URLSearchParams(data || {}).toString();
        location.href = 'uniwebview://result' + (query ? '?' + query : '');
    }

    window.UnityBridge = { inApp, getUserId, closeWebView, sendResult };

    if (!inApp) return;

    function addBackButton() {
        const style = document.createElement('style');
        style.textContent = `
            .user-bar { display: none !important; }

            /* 米色圓形、只有箭頭 */
            #unity-back-btn {
                flex: 0 0 auto;
                width: 44px;
                height: 44px;
                padding: 0;
                display: flex;
                align-items: center;
                justify-content: center;
                color: #5A4632;
                background: #F8F2E4;
                border: 2px solid #8B7B6B;
                border-radius: 50%;
                cursor: pointer;
                -webkit-tap-highlight-color: transparent;
            }
            #unity-back-btn svg { width: 22px; height: 22px; }
            #unity-back-btn:active { transform: scale(0.92); }

            /* 有搜尋列(食譜頁)：放在搜尋框左邊 */
            .search-bar.has-unity-back {
                align-items: center;
                gap: 10px;
            }

            /* 小遊戲頁：左上角箭頭取代原本的「回主選單」「返回」按鈕 */
            .unity-in-game .start-screen button[onclick*="index.html"],
            .unity-in-game .game-header .back-btn { display: none !important; }
            /* 遊戲中標題列左右留空間，避免被箭頭蓋到、標題也保持置中 */
            .unity-in-game .game-header { padding: 0 52px; }
            /* 結算畫面已經有「回主選單」，不顯示左上角箭頭 */
            .game-page.showing-result #unity-back-btn { display: none !important; }

            /* 遊戲選單頁、小遊戲頁：放在綠色底的左上角 */
            #unity-back-btn.in-wrapper {
                position: absolute;
                top: 12px;
                left: 12px;
                z-index: 10;
                box-shadow: 0 2px 6px rgba(0, 0, 0, 0.2);
            }

            /* 其他頁面：固定在畫面左上角 */
            #unity-back-btn.floating {
                position: fixed;
                top: max(12px, env(safe-area-inset-top));
                left: 12px;
                z-index: 99999;
                box-shadow: 0 2px 6px rgba(0, 0, 0, 0.2);
            }
        `;
        document.head.appendChild(style);

        const btn = document.createElement('button');
        btn.id = 'unity-back-btn';
        btn.type = 'button';
        btn.setAttribute('aria-label', '返回遊戲');
        btn.innerHTML =
            '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="3" ' +
            'stroke-linecap="round" stroke-linejoin="round"><path d="M15 5l-7 7 7 7"/></svg>';

        const searchBar = document.querySelector('.search-bar');
        const pageWrapper = document.querySelector('.page-wrapper');   // 遊戲選單頁
        const gamePage = document.querySelector('.game-page');         // 單一小遊戲頁

        if (gamePage) {
            // 小遊戲裡：回到遊戲選單(跟原本「回主選單」一樣)
            btn.setAttribute('aria-label', '回主選單');
            btn.addEventListener('click', () => { location.href = withUserId('../index.html'); });
            document.body.classList.add('unity-in-game');
            btn.classList.add('in-wrapper');
            gamePage.appendChild(btn);
            return;
        }

        // 其他頁面：關掉網頁回到 Unity
        btn.addEventListener('click', closeWebView);

        if (searchBar) {
            searchBar.classList.add('has-unity-back');
            searchBar.insertBefore(btn, searchBar.firstChild);
        } else if (pageWrapper) {
            btn.classList.add('in-wrapper');
            pageWrapper.appendChild(btn);
        } else {
            btn.classList.add('floating');
            document.body.appendChild(btn);
        }
    }

    // 站內連結(例如遊戲選單的卡片)都帶上 userId
    function tagLinks() {
        document.querySelectorAll('a[href]').forEach((a) => {
            a.setAttribute('href', withUserId(a.getAttribute('href')));
        });
    }

    // 結算畫面的「回主選單」也帶上 userId 回去
    document.addEventListener('click', (e) => {
        const home = e.target.closest && e.target.closest('#result-home');
        if (!home) return;
        e.preventDefault();
        e.stopImmediatePropagation();
        location.href = withUserId('../index.html');
    }, true);

    function init() {
        tagLinks();
        addBackButton();
    }

    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', init);
    } else {
        init();
    }
})();
