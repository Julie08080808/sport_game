// ==========================================
// 銀髮族健康問答 - 前端邏輯
// ==========================================
// 設計重點:
// 1. 答案驗證透過 POST /api/quiz/answer 由後端做(避免 F12 偷看答案)
// 2. 一題一題進行,每題答完顯示對錯 + 解釋
// 3. 全部答完顯示總成績
// 4. QUIZ_COUNT 一個變數控制要出幾題
// 5. 支援圖片題:題目有 image_url 時自動顯示圖片,文字題自動隱藏
// 6. 題型透過「網址參數」控制,介面不提供切換按鈕
//    一般使用者:  /quiz              → 混合隨機
//    demo 展示用:  /quiz?type=image   → 只出圖片題
//                 /quiz?type=text    → 只出文字題

const API_QUIZ = "/api/quiz";
const IMAGE_BASE_URL = "/image";

// 預設出題數,未來改這裡就好
const QUIZ_COUNT = 5;

// 從網址讀取題型參數(沒有帶就是 all)
// 例如 http://localhost:8000/quiz?type=image
const QUIZ_TYPE = new URLSearchParams(window.location.search).get('type') || 'all';

// 遊戲狀態
let questions = [];        // 本回合的題目
let currentIndex = 0;      // 目前在第幾題(0-based)
let correctCount = 0;      // 答對幾題

// ==========================================
// 初始化:顯示題庫總數
// ==========================================
async function init() {
    try {
        const res = await fetch(`${API_QUIZ}/total?type=${QUIZ_TYPE}`);
        const data = await res.json();

        // 只有在使用 demo 參數時才顯示題型標記,一般使用者看不到
        const typeLabel = QUIZ_TYPE === 'image' ? '(圖片題)'
                        : QUIZ_TYPE === 'text'  ? '(文字題)'
                        : '';

        document.getElementById('total-info').textContent =
            `題庫共有 ${data.total} 題${typeLabel},本次將隨機出 ${Math.min(QUIZ_COUNT, data.total)} 題`;
    } catch (err) {
        document.getElementById('total-info').textContent = '無法連接題庫,請確認伺服器是否啟動';
    }
}

// ==========================================
// 開始作答
// ==========================================
async function startQuiz() {
    try {
        const res = await fetch(
            `${API_QUIZ}/questions?count=${QUIZ_COUNT}&mode=random&type=${QUIZ_TYPE}`
        );
        if (!res.ok) {
            const err = await res.json();
            alert('載入題目失敗:' + (err.detail || '未知錯誤'));
            return;
        }
        questions = await res.json();
        currentIndex = 0;
        correctCount = 0;

        document.getElementById('start-screen').style.display = 'none';
        document.getElementById('result-screen').style.display = 'none';
        document.getElementById('quiz-screen').style.display = 'block';

        renderQuestion();
    } catch (err) {
        alert('連線失敗,請確認伺服器是否啟動');
    }
}

// ==========================================
// 顯示當前題目
// ==========================================
function renderQuestion() {
    const q = questions[currentIndex];
    const total = questions.length;

    // 進度顯示
    document.getElementById('progress-text').textContent =
        `第 ${currentIndex + 1} 題 / 共 ${total} 題`;
    document.getElementById('progress-fill').style.width =
        `${((currentIndex) / total) * 100}%`;

    // 題目內容
    document.getElementById('question-no').textContent = `題號 ${q.question_no}`;
    document.getElementById('question-text').textContent = q.question;
    document.getElementById('option-a-text').textContent = q.option_a;
    document.getElementById('option-b-text').textContent = q.option_b;

    // --- 圖片題處理 ---
    // 有 image_url 就顯示圖片,沒有就隱藏。兩種題型共用同一套渲染流程。
    const imgEl = document.getElementById('question-image');
    if (q.image_url) {
        imgEl.src = `${IMAGE_BASE_URL}/${q.image_url}`;
        imgEl.alt = q.question;   // 無障礙:螢幕閱讀器可讀出題目
        imgEl.style.display = 'block';
    } else {
        imgEl.style.display = 'none';
        imgEl.removeAttribute('src');
        imgEl.alt = '';
    }

    // 重置按鈕狀態
    document.getElementById('btn-a').disabled = false;
    document.getElementById('btn-b').disabled = false;
    document.getElementById('btn-a').classList.remove('selected', 'correct', 'wrong');
    document.getElementById('btn-b').classList.remove('selected', 'correct', 'wrong');

    // 隱藏回饋區
    document.getElementById('feedback-area').style.display = 'none';
}

// ==========================================
// 提交答案(送到後端驗證)
// ==========================================
async function submitAnswer(userAnswer) {
    const q = questions[currentIndex];

    // 鎖按鈕,防止重複點擊
    document.getElementById('btn-a').disabled = true;
    document.getElementById('btn-b').disabled = true;

    // 標記使用者選的那個
    document.getElementById(`btn-${userAnswer.toLowerCase()}`).classList.add('selected');

    try {
        const res = await fetch(`${API_QUIZ}/answer`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ question_id: q.id, user_answer: userAnswer })
        });
        const data = await res.json();

        // 視覺標記正確/錯誤按鈕
        const correctBtnId = `btn-${data.correct_answer.toLowerCase()}`;
        document.getElementById(correctBtnId).classList.add('correct');
        if (!data.correct) {
            document.getElementById(`btn-${userAnswer.toLowerCase()}`).classList.add('wrong');
        }

        // 顯示回饋
        const resultEl = document.getElementById('feedback-result');
        if (data.correct) {
            resultEl.textContent = '✓ 答對了!';
            resultEl.className = 'feedback-result feedback-correct';
            correctCount++;
        } else {
            resultEl.textContent = '✗ 答錯了';
            resultEl.className = 'feedback-result feedback-wrong';
        }

        document.getElementById('feedback-explanation-text').textContent = data.explanation;
        document.getElementById('feedback-area').style.display = 'block';

        // 自動捲動到回饋區
        document.getElementById('feedback-area').scrollIntoView({ behavior: 'smooth', block: 'center' });

        // 最後一題時,把「下一題」按鈕改成「看結果」
        if (currentIndex === questions.length - 1) {
            document.getElementById('next-btn').textContent = '看作答結果';
        }
    } catch (err) {
        alert('提交答案失敗,請檢查連線');
        document.getElementById('btn-a').disabled = false;
        document.getElementById('btn-b').disabled = false;
    }
}

// ==========================================
// 下一題 / 結算
// ==========================================
function nextQuestion() {
    currentIndex++;
    if (currentIndex >= questions.length) {
        showResult();
    } else {
        renderQuestion();
        // 重置「下一題」文字
        document.getElementById('next-btn').textContent = '下一題';
        // 捲回頂部
        window.scrollTo({ top: 0, behavior: 'smooth' });
    }
}

// ==========================================
// 結算畫面
// ==========================================
function showResult() {
    document.getElementById('quiz-screen').style.display = 'none';
    document.getElementById('result-screen').style.display = 'block';

    document.getElementById('score-correct').textContent = correctCount;
    document.getElementById('score-total').textContent = questions.length;

    // 依答對題數給不同鼓勵語(固定 5 題制)
    let comment = '';
    if (correctCount === 5)      comment = '恭喜全對,獲得 "?" 經驗值';
    else if (correctCount === 4) comment = '恭喜答對 4 題,獲得 "?" 經驗值';
    else if (correctCount === 3) comment = '恭喜答對 3 題,獲得 "?" 經驗值';
    else if (correctCount === 2) comment = '恭喜答對 2 題,獲得 "?" 經驗值';
    else if (correctCount === 1) comment = '恭喜答對 1 題,獲得 "?" 經驗值';
    else                         comment = '加油,未獲得經驗值';

    document.getElementById('score-comment').textContent = comment;
}

// ==========================================
// 重玩
// ==========================================
function restartQuiz() {
    document.getElementById('result-screen').style.display = 'none';
    document.getElementById('start-screen').style.display = 'block';
    init();
}

// 啟動
init();
