const API_URL = "http://localhost:8000/api";
const IMAGE_BASE_URL = "http://localhost:8000/image";
let allRecipes = [];
let swiperInstance = null;

// 新增：統一格式化食材字串的輔助函式
function formatIngredientString(ingStr) {
    // 使用正則表達式尋找數字並透過 parseFloat 去除多餘的 .00
    return ingStr.replace(/(\d+\.\d+)/g, (match) => parseFloat(match).toString());
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
        // --- 修改處：處理卡牌上的食材字串 ---
        const formattedIngredients = recipe.ingredients 
            ? recipe.ingredients.map(ing => formatIngredientString(ing)).join('、') 
            : '';
        // ----------------------------------

        return `
            <div class="swiper-slide">
                <div class="recipe-card" onclick="showDetails(${recipe.id}, '${recipe.name}')">
                    <img src="${IMAGE_BASE_URL}/${recipe.image_url}" class="recipe-img">
                    <div class="recipe-info">
                        <h3>${recipe.name}</h3>
                        <p><strong>份量：</strong>${recipe.servings || '2人份'}</p>
                        <p class="ingredients-list">
                            <strong>材料：</strong><br>
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
        
        const ingredientsHTML = recipe.ingredients ? recipe.ingredients.map(ing => {
            // 先統一處理數字格式
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

        const contentArea = document.getElementById('modal-content-area');
        contentArea.innerHTML = `
            <img src="${IMAGE_BASE_URL}/${recipe.image_url}" class="modal-hero-img">
            <div class="modal-padding">
                <h2 class="modal-recipe-title">${recipe.name}</h2>
                <div class="modal-section-title">所需材料</div>
                <div class="modal-ingredients-grid">
                    ${ingredientsHTML}
                </div>
                <div class="modal-section-title">作法步驟</div>
                <div class="modal-steps-list">
                    ${steps.map(s => `
                        <div class="modal-step">
                            <span class="step-num">第 ${s.step_number} 步</span>
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
    document.getElementById('detail-modal').style.display = "none";
    document.body.style.overflow = 'auto';
}

window.onclick = (event) => {
    const modal = document.getElementById('detail-modal');
    if (event.target == modal) {
        closeModal();
    }
};

fetchRecipes();