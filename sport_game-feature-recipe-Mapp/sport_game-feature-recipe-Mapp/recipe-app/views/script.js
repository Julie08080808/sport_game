// API 改為相對路徑(因為前後端同源,部署時更彈性)
const API_URL = "/api";
const IMAGE_BASE_URL = "/image";
let allRecipes = [];
let swiperInstance = null;
let currentAudio = null; // 用於儲存當前播放的音訊物件

// 水果季節畫面用的狀態
let fruitSeasonData = null;   // 抓過一次就快取，避免每次點「水果」都重打 API
let activeSeasonIndex = 0;
let fruitSwiperInstance = null;

const FRUIT_CATEGORY_ID = 8; // 對應資料庫 categories.id = 8（水果）

// 統一格式化食材字串(去除多餘的 .00)
function formatIngredientString(ingStr) {
    return ingStr.replace(/(\d+\.\d+)/g, (match) => parseFloat(match).toString());
}

// 顯示登入狀態
function renderUserBar() {
    const bar = document.getElementById('user-bar');
    if (!bar) return;
    const user = sessionStorage.getItem('username');
    if (user) {
        bar.innerHTML = `
            <span>👤 ${user}</span>
            <button class="user-btn" onclick="logout()">登出</button>
        `;
    } else {
        bar.innerHTML = `<a class="user-btn" href="/login">登入 / 註冊</a>`;
    }
}

function logout() {
    sessionStorage.removeItem('username');
    sessionStorage.removeItem('userId');
    renderUserBar();
}

// 核心語音播放函數
async function speak(text, elementId, isSSML = false, checkmarkId = null) {
    // 如果有正在播放的音訊，先停止
    if (currentAudio) {
        currentAudio.pause();
        currentAudio = null;
    }

    const targetElement = document.getElementById(elementId);

    // 開始播放前增加發亮效果
    if (targetElement) targetElement.classList.add('highlight');

    try {
        const response = await fetch(`${API_URL}/tts`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ text: text, is_ssml: isSSML })
        });

        if (!response.ok) throw new Error("語音請求失敗");

        const blob = await response.blob();
        const url = URL.createObjectURL(blob);
        currentAudio = new Audio(url);

        currentAudio.onended = () => {
            // 播放結束：移除發亮
            if (targetElement) targetElement.classList.remove('highlight');

            // 如果有指定的打勾 ID，則顯示打勾
            if (checkmarkId) {
                const check = document.getElementById(checkmarkId);
                if (check) check.classList.add('active');
            }
            currentAudio = null;
        };

        currentAudio.play();
    } catch (error) {
        console.error("語音播放出錯:", error);
        if (targetElement) targetElement.classList.remove('highlight');
    }
}

async function fetchRecipes() {
    try {
        const response = await fetch(`${API_URL}/recipes`);
        allRecipes = (await response.json()).filter(r => r.category_id !== FRUIT_CATEGORY_ID);
        renderRecipes(allRecipes);
    } catch (error) {
        console.error("載入失敗:", error);
    }
}

function renderRecipes(recipes) {
    const wrapper = document.getElementById('recipe-wrapper');
    if (swiperInstance) swiperInstance.destroy(true, true);

    wrapper.innerHTML = recipes.map(recipe => {
        const formattedIngredients = recipe.ingredients
            ? recipe.ingredients.map(ing => formatIngredientString(ing)).join('、')
            : '';

        const tagsHTML = (recipe.tags && recipe.tags.length > 0)
            ? `<div class="recipe-tags">${recipe.tags.map(tag => `<span class="tag-badge">${tag}</span>`).join('')}</div>`
            : '';

        return `
            <div class="swiper-slide">
                <div class="recipe-card" onclick="showDetails(${recipe.id}, '${recipe.name}')">
                    <img src="${IMAGE_BASE_URL}/${recipe.image_url}" class="recipe-img">
                    <div class="recipe-info">
                        <h3>${recipe.name}</h3>
                        ${tagsHTML}
                        <p><strong>份量:</strong>${recipe.servings || '2人份'}</p>
                        <p class="ingredients-list">
                            <strong>材料:</strong><br>
                            ${formattedIngredients}
                        </p>
                        <div class="view-more-hint">查看更多 ></div>
                    </div>
                </div>
            </div>
        `;
    }).join('');

    swiperInstance = new Swiper('.recipe-swiper', {
        slidesPerView: 'auto',
        centeredSlides: true,
        spaceBetween: 20,
        loop: recipes.length > 1,
        pagination: { el: '.swiper-pagination', clickable: true },
    });
}

function filterRecipes(catId) {
    const btn = event.target;
    document.querySelectorAll('.filter-btn').forEach(b => b.classList.remove('active'));
    btn.classList.add('active');

    // 切換分類時，清空搜尋框，避免搜尋結果跟分類篩選互相干擾
    const searchInput = document.getElementById('search-input');
    if (searchInput) searchInput.value = '';

    if (catId === FRUIT_CATEGORY_ID) {
        // 切到水果季節畫面
        document.getElementById('recipe-view').style.display = 'none';
        document.getElementById('fruit-view').style.display = 'block';
        showFruitSeasonView();
        return;
    }

    // 其他分類：切回一般食譜畫面
    document.getElementById('fruit-view').style.display = 'none';
    document.getElementById('recipe-view').style.display = 'block';

    const filtered = (catId === 'all')
        ? allRecipes
        : allRecipes.filter(r => r.category_id === catId);
    renderRecipes(filtered);
}

// 搜尋食譜名稱或食材（子字串比對，符合其中一項就顯示）
function handleSearch() {
    const keyword = document.getElementById('search-input').value.trim();

    // 搜尋時一律切回一般食譜畫面（水果季節畫面資料來源不同，不在搜尋範圍內）
    document.getElementById('fruit-view').style.display = 'none';
    document.getElementById('recipe-view').style.display = 'block';

    if (!keyword) {
        // 清空搜尋框時，恢復顯示全部食譜，並把「全部」按鈕標成選取狀態
        document.querySelectorAll('.filter-btn').forEach(b => b.classList.remove('active'));
        const allBtn = document.querySelector('.filter-btn[onclick*="\'all\'"]');
        if (allBtn) allBtn.classList.add('active');
        renderRecipes(allRecipes);
        return;
    }

    // 搜尋時取消分類按鈕的選取樣式，避免顯示混淆
    document.querySelectorAll('.filter-btn').forEach(b => b.classList.remove('active'));

    const filtered = allRecipes.filter(recipe => {
        const nameMatch = recipe.name && recipe.name.includes(keyword);
        const ingredientMatch = recipe.ingredients && recipe.ingredients.some(ing => ing.includes(keyword));
        return nameMatch || ingredientMatch;
    });

    renderRecipes(filtered);
}

// ===== 水果季節畫面 =====

async function showFruitSeasonView() {
    // 已經抓過就直接重繪，不用每次點都重打 API
    if (fruitSeasonData) {
        renderFruitSeasons(fruitSeasonData);
        return;
    }
    try {
        const response = await fetch(`${API_URL}/fruits/by-season`);
        if (!response.ok) throw new Error("水果資料載入失敗");
        fruitSeasonData = await response.json();
        renderFruitSeasons(fruitSeasonData);
    } catch (error) {
        console.error("載入當季水果失敗:", error);
        document.getElementById('fruit-season-wrapper').innerHTML =
            `<div class="swiper-slide"><p class="season-empty">水果資料載入失敗，請稍後再試</p></div>`;
    }
}

// data 格式: [{ season: '全年', fruits: [{id, name, image_url, serving_desc}] }, ...]
function renderFruitSeasons(data) {
    const tabsEl = document.getElementById('season-tabs');

    tabsEl.innerHTML = data.map((group, idx) => `
        <button type="button" class="season-tab${idx === activeSeasonIndex ? ' active' : ''}" data-index="${idx}">
            ${group.season}
        </button>
    `).join('');

    tabsEl.querySelectorAll('.season-tab').forEach(btn => {
        btn.addEventListener('click', () => {
            activeSeasonIndex = parseInt(btn.dataset.index, 10);
            renderFruitGrid(data[activeSeasonIndex]);
            tabsEl.querySelectorAll('.season-tab').forEach((b, i) => {
                b.classList.toggle('active', i === activeSeasonIndex);
            });
        });
    });

    renderFruitGrid(data[activeSeasonIndex]);
}

// 把陣列切成每組固定數量的小陣列，例如 chunkArray([1,2,3,4,5], 4) => [[1,2,3,4],[5]]
function chunkArray(arr, size) {
    const chunks = [];
    for (let i = 0; i < arr.length; i += size) {
        chunks.push(arr.slice(i, i + size));
    }
    return chunks;
}

// 依目前選中的季節，把水果每 4 個切成一頁（2x2），用 Swiper 左右滑動切頁
function renderFruitGrid(group) {
    const wrapperEl = document.getElementById('fruit-wrapper');

    // 換季節或重繪前，先銷毀舊的 Swiper 實例，避免殘留狀態
    if (fruitSwiperInstance) {
        fruitSwiperInstance.destroy(true, true);
        fruitSwiperInstance = null;
    }

    if (!group || !group.fruits || group.fruits.length === 0) {
        wrapperEl.innerHTML = `<div class="swiper-slide"><p class="season-empty">這個季節目前還沒有資料</p></div>`;
        return;
    }

    const pages = chunkArray(group.fruits, 4);

    wrapperEl.innerHTML = pages.map(pageFruits => `
        <div class="swiper-slide">
            <div class="fruit-page">
                ${pageFruits.map(fruit => `
                    <div class="fruit-card">
                        <img src="${IMAGE_BASE_URL}/${fruit.image_url}" class="fruit-card-img" alt="${fruit.name}">
                        <div class="fruit-card-info">
                            <h3>${fruit.name}</h3>
                            <p><strong>一份約：</strong>${fruit.serving_desc || '未提供'}</p>
                        </div>
                    </div>
                `).join('')}
            </div>
        </div>
    `).join('');

    fruitSwiperInstance = new Swiper('.fruit-swiper', {
        slidesPerView: 1,
        spaceBetween: 0,
        loop: false,
    });
}

// ===== 食譜詳情 Modal（維持原本邏輯） =====

// 讀取這道食譜之前存過的筆記（用 localStorage，只存在這台裝置這個瀏覽器）
function getRecipeNote(recipeId) {
    try {
        return localStorage.getItem(`recipe-note-${recipeId}`) || '';
    } catch (error) {
        console.error('讀取筆記失敗:', error);
        return '';
    }
}

// 使用者打字時即時把筆記存進 localStorage
function saveRecipeNote(recipeId) {
    try {
        const textarea = document.getElementById('recipe-note');
        localStorage.setItem(`recipe-note-${recipeId}`, textarea.value);
    } catch (error) {
        console.error('儲存筆記失敗:', error);
    }
}

async function showDetails(id, name) {
    try {
        const recipe = allRecipes.find(r => r.id === id);
        const res = await fetch(`${API_URL}/recipes/${id}/steps`);
        const steps = await res.json();

        // 渲染材料 HTML - 左名稱右數量排版
        const ingredientsHTML = recipe.ingredients ? recipe.ingredients.map((ing, idx) => {
            const cleanIng = formatIngredientString(ing.trim());
            const parts = cleanIng.split(' ');
            const ingName = parts[0];
            const ingAmount = parts.slice(1).join(' ');

            return `
                <div class="ingredient-row">
                    <span class="ingredient-name">${ingName}</span>
                    <span class="ingredient-amount">${ingAmount}</span>
                </div>
            `;
        }).join('') : '暫無材料資訊';

        // 準備所有食材文字用於一次播放 - 包含「所需材料」標題
        const allIngredientsText = recipe.ingredients
            ? '所需材料，' + recipe.ingredients.map(ing => formatIngredientString(ing.trim())).join('，')
            : '';

        const contentArea = document.getElementById('modal-content-area');
        contentArea.innerHTML = `
            <img src="${IMAGE_BASE_URL}/${recipe.image_url}" class="modal-hero-img">
            <div class="modal-padding">
                <h2 class="modal-recipe-title">${recipe.name}</h2>

                <div class="ingredients-section-header">
                    <span class="modal-section-title">所需材料</span>
                    <button class="tts-btn" onclick="speak('${allIngredientsText}', 'ingredients-section')">🔊</button>
                </div>
                <div class="modal-ingredients-grid" id="all-ingredients-container">
                    ${ingredientsHTML}
                </div>

                <div class="modal-section-title">作法步驟</div>
                <div class="modal-steps-list">
                    ${steps.map((s, idx) => `
                        <div class="modal-step" id="step-block-${idx}">
                            <div class="step-header">
                                <span class="step-num">第 ${s.step_number} 步</span>
                                <div class="step-controls">
                                    <button class="tts-btn" onclick="speak('${s.description}', 'step-block-${idx}', false, 'step-check-${idx}')">🔊</button>
                                    <span class="checkmark" id="step-check-${idx}">✅</span>
                                </div>
                            </div>
                            <p>${s.description}</p>
                        </div>
                    `).join('')}
                </div>

                <div class="modal-section-title">我的筆記</div>
                <div class="note-section">
                    <textarea
                        id="recipe-note"
                        class="note-textarea"
                        placeholder="在這裡寫下你的心得、調整份量或做法上的小提醒吧..."
                        oninput="saveRecipeNote(${recipe.id})"
                    >${getRecipeNote(recipe.id)}</textarea>
                    <div class="note-saved-hint" id="note-saved-hint">已自動儲存在這台裝置</div>
                </div>
            </div>
        `;

        const modal = document.getElementById('detail-modal');
        modal.style.display = "block";
        modal.scrollTop = 0;
        document.body.style.overflow = 'hidden';
    } catch (error) {
        console.error("載入詳細步驟出錯:", error);
    }
}

function closeModal() {
    if (currentAudio) {
        currentAudio.pause();
        currentAudio = null;
    }
    document.getElementById('detail-modal').style.display = "none";
    document.body.style.overflow = 'auto';
}

window.onclick = (event) => {
    const modal = document.getElementById('detail-modal');
    if (event.target == modal) {
        closeModal();
    }
};

renderUserBar();
fetchRecipes();