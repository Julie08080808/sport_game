// API 改為相對路徑(因為前後端同源,部署時更彈性)
const API_URL = "/api";
const IMAGE_BASE_URL = "/image";
let allRecipes = [];
let swiperInstance = null;
let currentAudio = null; // 用於儲存當前播放的音訊物件

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
        allRecipes = await response.json();
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

        return `
            <div class="swiper-slide">
                <div class="recipe-card" onclick="showDetails(${recipe.id}, '${recipe.name}')">
                    <img src="${IMAGE_BASE_URL}/${recipe.image_url}" class="recipe-img">
                    <div class="recipe-info">
                        <h3>${recipe.name}</h3>
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

    swiperInstance = new Swiper('.swiper', {
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

    const filtered = (catId === 'all')
        ? allRecipes
        : allRecipes.filter(r => r.category_id === catId);
    renderRecipes(filtered);
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