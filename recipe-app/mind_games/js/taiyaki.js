'use strict';

// ╔══════════════════════════════════════════════════════════════╗
// ║  替換自己的圖片                                               ║
// ║  將圖片放入  images/taiyaki/  資料夾（.png / .jpg / .svg）    ║
// ║  修改下方路徑即可；找不到圖片時自動顯示備用色塊樣式             ║
// ╚══════════════════════════════════════════════════════════════╝
const CELL_IMAGES = {
  empty:    '../images/taiyaki/empty.svg',
  batter:   '../images/taiyaki/batter.svg',
  passion:  '../images/taiyaki/passion.svg',
  bamboo:   '../images/taiyaki/bamboo.svg',
  mushroom: '../images/taiyaki/mushroom.svg',
};

// ─── Fillings ─────────────────────────────────────────────────────────────────

const FILLINGS = {
  batter:   { id: 'batter',   name: '麵糊',    emoji: '🫓', cssClass: 'batter'   },
  passion:  { id: 'passion',  name: '百香果醬', emoji: '🌟', cssClass: 'passion'  },
  bamboo:   { id: 'bamboo',   name: '茭白筍丁', emoji: '🌿', cssClass: 'bamboo'   },
  mushroom: { id: 'mushroom', name: '香菇',     emoji: '🍄', cssClass: 'mushroom' },
};

// ─── All Questions ────────────────────────────────────────────────────────────

const ALL_QUESTIONS = [
  // ── Stage 1：麵糊對稱 ──────────────────────────────────────────
  {
    id: 1, rows: 2, cols: 2,
    stage: 1, stageLabel: '第一階段：麵糊對稱',
    leftCells: [
      { row: 0, col: 0, filling: 'batter' },
      { row: 1, col: 1, filling: 'batter' },
    ],
  },
  {
    id: 2, rows: 3, cols: 2,
    stage: 1, stageLabel: '第一階段：麵糊對稱',
    leftCells: [
      { row: 0, col: 0, filling: 'batter' },
      { row: 1, col: 0, filling: 'batter' },
      { row: 2, col: 1, filling: 'batter' },
    ],
  },

  // ── Stage 2：加入一種餡料 ──────────────────────────────────────
  {
    id: 3, rows: 3, cols: 2,
    stage: 2, stageLabel: '第二階段：加入一種餡料',
    leftCells: [
      { row: 0, col: 0, filling: 'batter'  },
      { row: 0, col: 1, filling: 'passion' },
      { row: 2, col: 1, filling: 'batter'  },
    ],
  },
  {
    id: 4, rows: 4, cols: 2,
    stage: 2, stageLabel: '第二階段：加入一種餡料',
    leftCells: [
      { row: 1, col: 0, filling: 'batter' },
      { row: 2, col: 0, filling: 'bamboo' },
      { row: 0, col: 1, filling: 'bamboo' },
      { row: 3, col: 1, filling: 'batter' },
    ],
  },

  // ── Stage 3：多種埔里特產餡料 ──────────────────────────────────
  {
    id: 5, rows: 4, cols: 2,
    stage: 3, stageLabel: '第三階段：多種埔里特產餡料',
    leftCells: [
      { row: 0, col: 0, filling: 'passion' },
      { row: 3, col: 0, filling: 'batter'  },
      { row: 1, col: 1, filling: 'batter'  },
      { row: 2, col: 1, filling: 'bamboo'  },
    ],
  },
  {
    id: 6, rows: 4, cols: 2,
    stage: 3, stageLabel: '第三階段：多種埔里特產餡料',
    leftCells: [
      { row: 0, col: 0, filling: 'mushroom' },
      { row: 2, col: 0, filling: 'passion'  },
      { row: 1, col: 1, filling: 'bamboo'   },
      { row: 3, col: 1, filling: 'batter'   },
    ],
  },
];

// ─── Difficulty Config ────────────────────────────────────────────────────────

const DIFFICULTY = {
  easy:   { label: '簡單', cssClass: 'easy',   questions: ALL_QUESTIONS.slice(0, 2), timeLimit: null },
  normal: { label: '普通', cssClass: 'normal', questions: ALL_QUESTIONS,              timeLimit: null },
  hard:   { label: '困難', cssClass: 'hard',   questions: ALL_QUESTIONS,              timeLimit: 90  },
};

// ─── State ────────────────────────────────────────────────────────────────────

let state = {
  qIdx:            0,
  seconds:         0,
  timer:           null,
  active:          false,
  selectedFilling: 'batter',
  rightCells:      [],
  difficulty:      'normal',
  questions:       ALL_QUESTIONS,
  timeLimit:       null,
  timeLeft:        0,
};

// ─── DOM ──────────────────────────────────────────────────────────────────────

const $start     = document.getElementById('start-screen');
const $game      = document.getElementById('game-screen');
const $result    = document.getElementById('result-screen');
const $dialog    = document.getElementById('dialog-overlay');
const $timer     = document.getElementById('timer-value');
const $timerLbl  = document.getElementById('timer-label');
const $qLabel    = document.getElementById('q-label');
const $stageBnr  = document.getElementById('stage-banner');
const $leftGrid  = document.getElementById('left-grid');
const $rightGrid = document.getElementById('right-grid');
const $fillPanel = document.getElementById('filling-panel');
const $fillBtns  = document.getElementById('filling-buttons');
const $confirm   = document.getElementById('confirm-btn');
const $reset     = document.getElementById('reset-btn');
const $diffBadge = document.getElementById('diff-badge');
const $dbEmoji   = document.getElementById('dialog-emoji');
const $dbTitle   = document.getElementById('dialog-title');
const $dbMsg     = document.getElementById('dialog-msg');
const $dbBtns    = document.getElementById('dialog-btns');
const $toast     = document.getElementById('toast-msg');

// ─── Toast ────────────────────────────────────────────────────────────────────

let _toastTimer = null;
function showToast(msg) {
  $toast.textContent = msg;
  $toast.classList.add('show');
  clearTimeout(_toastTimer);
  _toastTimer = setTimeout(() => $toast.classList.remove('show'), 2000);
}

// ─── Cell Content Helper ──────────────────────────────────────────────────────

function makeCellContent(fillingId) {
  const imgSrc = CELL_IMAGES[fillingId || 'empty'];
  const f = fillingId ? FILLINGS[fillingId] : null;
  const fallback = f
    ? `<span class="cell-emoji">${f.emoji}</span><span class="cell-label">${f.name}</span>`
    : `<span class="cell-hint">○</span>`;
  return `<img class="cell-img" src="${imgSrc}" alt=""
    onload="this.closest('.mold-cell').classList.add('has-img')"
    onerror="this.remove()">${fallback}`;
}

// ─── Game Start ───────────────────────────────────────────────────────────────

function startGame(diff) {
  if (diff !== undefined) state.difficulty = diff;
  const diffCfg      = DIFFICULTY[state.difficulty];
  state.questions    = diffCfg.questions;
  state.timeLimit    = diffCfg.timeLimit;
  state.qIdx         = 0;
  state.seconds      = 0;
  state.active       = true;
  clearInterval(state.timer);

  $diffBadge.textContent = diffCfg.label;
  $diffBadge.className   = 'diff-badge ' + diffCfg.cssClass;

  if (state.timeLimit) {
    state.timeLeft     = state.timeLimit;
    $timerLbl.textContent = '⏱ 倒數';
    $timer.textContent = formatTime(state.timeLimit);
    $timer.className   = 'stat-value';
    state.timer = setInterval(tickDown, 1000);
  } else {
    $timerLbl.textContent = '⏱ 計時';
    $timer.textContent = '0:00';
    $timer.className   = 'stat-value';
    state.timer = setInterval(tickUp, 1000);
  }

  $start.classList.add('hidden');
  $result.classList.add('hidden');
  $game.classList.remove('hidden');
  $dialog.classList.add('hidden');
  document.querySelector('.game-page').classList.add('in-game');

  loadQuestion(0);
}

// ─── Load Question ────────────────────────────────────────────────────────────

function loadQuestion(idx) {
  const q = state.questions[idx];
  state.rightCells      = [];
  state.selectedFilling = 'batter';

  $qLabel.textContent   = `第 ${idx + 1} 題 / 共 ${state.questions.length} 題`;
  $stageBnr.textContent = q.stageLabel;

  const colTemplate = `repeat(${q.cols}, 1fr)`;
  const rowTemplate = `repeat(${q.rows}, 1fr)`;

  // ── Left grid (read-only) ──
  $leftGrid.style.gridTemplateColumns = colTemplate;
  $leftGrid.style.gridTemplateRows    = rowTemplate;
  $leftGrid.innerHTML = '';
  for (let r = 0; r < q.rows; r++) {
    for (let c = 0; c < q.cols; c++) {
      const cell = q.leftCells.find(lc => lc.row === r && lc.col === c);
      const div  = document.createElement('div');
      div.className = 'mold-cell';
      if (cell) div.classList.add(FILLINGS[cell.filling].cssClass);
      div.innerHTML = makeCellContent(cell ? cell.filling : null);
      $leftGrid.appendChild(div);
    }
  }

  // ── Right grid (player) ──
  $rightGrid.style.gridTemplateColumns = colTemplate;
  $rightGrid.style.gridTemplateRows    = rowTemplate;
  $rightGrid.innerHTML = '';
  for (let r = 0; r < q.rows; r++) {
    for (let c = 0; c < q.cols; c++) {
      const div = document.createElement('div');
      div.className   = 'mold-cell';
      div.dataset.row = r;
      div.dataset.col = c;
      div.innerHTML   = makeCellContent(null);
      div.addEventListener('click', () => onRightCellClick(r, c));
      $rightGrid.appendChild(div);
    }
  }

  // ── Filling panel (Stage 2 & 3) ──
  if (q.stage >= 2) {
    $fillPanel.classList.remove('hidden-panel');
    buildFillingButtons(q);
  } else {
    $fillPanel.classList.add('hidden-panel');
  }
}

// ─── Filling Buttons ──────────────────────────────────────────────────────────

function buildFillingButtons(q) {
  const used    = [...new Set(q.leftCells.map(c => c.filling))];
  const ordered = ['batter', ...used.filter(f => f !== 'batter')];

  $fillBtns.innerHTML = '';
  ordered.forEach(fid => {
    const f   = FILLINGS[fid];
    const btn = document.createElement('button');
    btn.className       = 'filling-btn' + (fid === state.selectedFilling ? ' selected' : '');
    btn.dataset.filling = fid;
    btn.innerHTML = `
      <span class="filling-btn-emoji">${f.emoji}</span>
      <span class="filling-btn-name">${f.name}</span>`;
    btn.addEventListener('click', () => {
      state.selectedFilling = fid;
      highlightSelectedFilling();
    });
    $fillBtns.appendChild(btn);
  });
}

function highlightSelectedFilling() {
  document.querySelectorAll('.filling-btn').forEach(btn => {
    btn.classList.toggle('selected', btn.dataset.filling === state.selectedFilling);
  });
}

// ─── Right Grid Interaction ───────────────────────────────────────────────────

function onRightCellClick(row, col) {
  const existingIdx = state.rightCells.findIndex(c => c.row === row && c.col === col);
  const existing    = existingIdx !== -1 ? state.rightCells[existingIdx] : null;
  const sel         = state.selectedFilling;

  if (sel === 'batter') {
    if (!existing) {
      state.rightCells.push({ row, col, filling: 'batter' });
    } else if (existing.filling === 'batter') {
      state.rightCells.splice(existingIdx, 1);
    } else {
      state.rightCells[existingIdx].filling = 'batter';
    }
  } else {
    if (!existing) {
      showToast('🔑 請先選「麵糊」，在格子鋪底後再加餡料！');
      return;
    }
    if (existing.filling === sel) {
      state.rightCells[existingIdx].filling = 'batter';
    } else {
      state.rightCells[existingIdx].filling = sel;
    }
  }

  renderRightGrid();
}

function renderRightGrid() {
  Array.from($rightGrid.children).forEach(div => {
    const row    = parseInt(div.dataset.row);
    const col    = parseInt(div.dataset.col);
    const placed = state.rightCells.find(c => c.row === row && c.col === col);

    div.className = 'mold-cell';
    if (placed) div.classList.add(FILLINGS[placed.filling].cssClass);
    div.innerHTML = makeCellContent(placed ? placed.filling : null);
  });
}

// ─── Confirm / Validate ───────────────────────────────────────────────────────

function onConfirm() {
  const q    = state.questions[state.qIdx];
  const cols = q.cols;

  const expected = q.leftCells.map(lc => ({
    row:     lc.row,
    col:     cols - 1 - lc.col,
    filling: lc.filling,
  }));

  let allCorrect = true;
  const resultMap = {};

  expected.forEach(exp => {
    const key   = `${exp.row},${exp.col}`;
    const found = state.rightCells.find(c => c.row === exp.row && c.col === exp.col);
    resultMap[key] = (found && found.filling === exp.filling) ? 'correct' : 'wrong';
    if (resultMap[key] === 'wrong') allCorrect = false;
  });

  state.rightCells.forEach(rc => {
    const key   = `${rc.row},${rc.col}`;
    const isExp = expected.some(e => e.row === rc.row && e.col === rc.col);
    if (!isExp) { resultMap[key] = 'wrong'; allCorrect = false; }
  });

  const filledKeys = new Set(state.rightCells.map(c => `${c.row},${c.col}`));
  expected.forEach(exp => {
    const key = `${exp.row},${exp.col}`;
    if (!filledKeys.has(key)) { resultMap[key] = 'wrong'; allCorrect = false; }
  });

  Array.from($rightGrid.children).forEach(div => {
    const key = `${div.dataset.row},${div.dataset.col}`;
    div.classList.remove('correct', 'wrong');
    if (resultMap[key]) div.classList.add(resultMap[key]);
  });

  if (allCorrect) {
    $rightGrid.classList.add('bounce-in');
    setTimeout(() => $rightGrid.classList.remove('bounce-in'), 400);
    setTimeout(() => {
      state.qIdx++;
      if (state.qIdx >= state.questions.length) {
        onAllDone();
      } else {
        loadQuestion(state.qIdx);
      }
    }, 900);
  } else {
    $rightGrid.classList.add('shake');
    setTimeout(() => $rightGrid.classList.remove('shake'), 500);
  }
}

function onReset() {
  state.rightCells = [];
  renderRightGrid();
  Array.from($rightGrid.children).forEach(div => div.classList.remove('correct', 'wrong'));
}

// ─── Timer ────────────────────────────────────────────────────────────────────

function formatTime(s) {
  const m = Math.floor(s / 60);
  return `${m}:${(s % 60).toString().padStart(2, '0')}`;
}

function tickUp() {
  state.seconds++;
  $timer.textContent = formatTime(state.seconds);
}

function tickDown() {
  state.timeLeft--;
  $timer.textContent = formatTime(state.timeLeft);
  $timer.className   = 'stat-value';
  if      (state.timeLeft <= 10) $timer.classList.add('danger');
  else if (state.timeLeft <= 30) $timer.classList.add('warn');

  if (state.timeLeft <= 0) {
    showResult(false);
  }
}

// ─── Completion ───────────────────────────────────────────────────────────────

function onAllDone() {
  clearInterval(state.timer);
  state.active = false;
  showResult(true);
}

// ─── Score ────────────────────────────────────────────────────────────────────

function calcScore() {
  const diffBonus = { easy: 0, normal: 100, hard: 200 };
  const totalQ    = state.questions.length;

  const completionPts = Math.round((state.qIdx / totalQ) * 500);
  const speedPts = state.timeLimit
    ? Math.round((state.timeLeft / state.timeLimit) * 300)
    : Math.max(0, Math.round(300 * (1 - state.seconds / 300)));
  const diffPts   = diffBonus[state.difficulty];

  return {
    completion: completionPts,
    speed:      speedPts,
    difficulty: diffPts,
    total:      Math.min(1000, completionPts + speedPts + diffPts),
  };
}

const ENCOURAGEMENTS = [
  '頭腦越用越靈光，今天又是充滿活力的一天！',
  '太棒了！活到老、學到老，您就是最棒的榜樣！',
  '有動腦、有運動，健康長壽隨時動！',
  '不簡單喔！今天的健康腦力大挑戰圓滿成功！',
  '不論對幾題，肯動腦嘗試就是滿分！',
  '動動腦、伸展身體，每天都要笑嘻嘻！',
  '多學習新知識，讓生活每天都多姿多彩！',
  '答題越來越熟練，您的記憶力真是一流！',
  '給自己一個大大的掌聲，今天又超越昨天囉！',
  '每天進步一點點，健康快樂多一點！',
  '多學一個知識，健康就多一份保障！',
  '答題就是動腦，每一題都在幫大腦做體操！',
  '活學活用小知識，生活健康又充實！',
  '學到的就是自己的，今天又比昨天更聰明囉！',
  '知識不嫌多，今天又認識了好多健康好朋友！',
  '不論對錯都是學習，您今天真的很努力！',
  '多看、多聽、多學習，快樂長壽跟著您！',
  '挑戰就是最好的鍛鍊，您的學習精神令人佩服！',
  '常常動腦思考，思緒永遠保持年輕！',
  '每天學點新常識，健康生活好輕鬆！',
];
function getEncouragement() {
  return ENCOURAGEMENTS[Math.floor(Math.random() * ENCOURAGEMENTS.length)];
}

function showResult(completed) {
  clearInterval(state.timer);
  state.active = false;
  const score = calcScore();

  document.getElementById('result-outcome').textContent = completed ? '🏆 全部完成！' : '⏰ 時間到了！';

  const bdC = document.getElementById('bd-completion');
  const bdS = document.getElementById('bd-speed');
  const bdD = document.getElementById('bd-difficulty');
  bdC.textContent = score.completion + ' 分';
  bdS.textContent = score.speed      + ' 分';
  bdD.textContent = score.difficulty + ' 分';
  bdC.classList.toggle('zero', score.completion === 0);
  bdS.classList.toggle('zero', score.speed      === 0);
  bdD.classList.toggle('zero', score.difficulty === 0);

  document.getElementById('result-encourage').textContent = getEncouragement();

  const starCount = score.total >= 700 ? 3 : score.total >= 400 ? 2 : 1;
  [1, 2, 3].forEach(i => {
    const el = document.getElementById('star-' + i);
    el.classList.remove('lit');
    if (i <= starCount) setTimeout(() => el.classList.add('lit'), 300 + i * 260);
  });

  const scoreEl = document.getElementById('result-score');
  scoreEl.textContent = '0';
  const target = score.total;
  const start  = performance.now();
  (function animate(now) {
    const p = Math.min((now - start) / 1200, 1);
    scoreEl.textContent = Math.round(target * (1 - Math.pow(1 - p, 3)));
    if (p < 1) requestAnimationFrame(animate);
  })(start);

  document.getElementById('result-retry').onclick = () => startGame();
  document.getElementById('result-home').onclick  = () => { location.href = '../index.html'; };

  $game.classList.add('hidden');
  $dialog.classList.add('hidden');
  $result.classList.remove('hidden');
  document.querySelector('.game-page').classList.add('showing-result');
}

// ─── Init ─────────────────────────────────────────────────────────────────────

['easy', 'normal', 'hard'].forEach(diff => {
  document.getElementById(`btn-${diff}`).addEventListener('click', () => startGame(diff));
});

$confirm.addEventListener('click', onConfirm);
$reset.addEventListener('click', onReset);
