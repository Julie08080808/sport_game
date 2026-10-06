'use strict';

// ─── Config ───────────────────────────────────────────────────────────────────

const KITCHEN_ITEMS = [
  { emoji: '🍳', name: '平底鍋' },
  { emoji: '🥄', name: '湯匙' },
  { emoji: '🍚', name: '飯碗' },
  { emoji: '🔪', name: '菜刀' },
  { emoji: '🧂', name: '鹽罐' },
  { emoji: '🥢', name: '筷子' },
];

const DIFFICULTY = {
  easy: {
    label: '簡單', cssClass: 'easy', totalTime: 90,
    levels: [
      { level: 1, rows: 2, cols: 3, pairs: 3, label: '第一關' },
      { level: 2, rows: 2, cols: 4, pairs: 4, label: '第二關' },
      { level: 3, rows: 2, cols: 5, pairs: 5, label: '第三關（最終關）' },
    ],
  },
  normal: {
    label: '普通', cssClass: 'normal', totalTime: 60,
    levels: [
      { level: 1, rows: 2, cols: 3, pairs: 3, label: '第一關' },
      { level: 2, rows: 2, cols: 4, pairs: 4, label: '第二關' },
      { level: 3, rows: 2, cols: 5, pairs: 5, label: '第三關（最終關）' },
    ],
  },
  hard: {
    label: '困難', cssClass: 'hard', totalTime: 40,
    levels: [
      { level: 1, rows: 2, cols: 4, pairs: 4, label: '第一關' },
      { level: 2, rows: 2, cols: 5, pairs: 5, label: '第二關' },
      { level: 3, rows: 3, cols: 4, pairs: 6, label: '第三關（最終關）' },
    ],
  },
};

// ─── State ────────────────────────────────────────────────────────────────────

let state = {
  level:           1,
  difficulty:      'normal',
  timeLeft:        60,
  cards:           [],
  flipped:         [],
  matched:         0,
  locked:          false,
  timer:           null,
  active:          false,
  levelsCompleted: 0,
};

// ─── DOM ──────────────────────────────────────────────────────────────────────

const $start    = document.getElementById('start-screen');
const $game     = document.getElementById('game-screen');
const $result   = document.getElementById('result-screen');
const $dialog   = document.getElementById('dialog-overlay');
const $board    = document.getElementById('game-board');
const $timer    = document.getElementById('timer-value');
const $matched  = document.getElementById('match-count');
const $total    = document.getElementById('total-count');
const $levelLbl = document.getElementById('level-label');
const $diffBadge= document.getElementById('diff-badge');
const $dbEmoji  = document.getElementById('dialog-emoji');
const $dbTitle  = document.getElementById('dialog-title');
const $dbMsg    = document.getElementById('dialog-msg');
const $dbBtns   = document.getElementById('dialog-btns');

// ─── Core Game ────────────────────────────────────────────────────────────────

function startLevel(level, diff) {
  if (diff) state.difficulty = diff;
  const diffCfg = DIFFICULTY[state.difficulty];
  const cfg     = diffCfg.levels[level - 1];

  state.level    = level;
  state.timeLeft = diffCfg.totalTime;
  state.flipped  = [];
  state.matched  = 0;
  state.locked   = false;
  state.active   = true;
  if (level === 1) state.levelsCompleted = 0;
  clearInterval(state.timer);

  const items = KITCHEN_ITEMS.slice(0, cfg.pairs);
  state.cards = shuffle(
    [...items, ...items].map((item, i) => ({ ...item, id: i, flipped: false, matched: false }))
  );

  $levelLbl.textContent  = cfg.label;
  $total.textContent     = cfg.pairs;
  $matched.textContent   = 0;
  $diffBadge.textContent = diffCfg.label;
  $diffBadge.className   = 'diff-badge ' + diffCfg.cssClass;

  updateTimerDisplay();
  updateDots(level);
  renderBoard(cfg);

  $start.classList.add('hidden');
  $result.classList.add('hidden');
  $game.classList.remove('hidden');
  $dialog.classList.add('hidden');
  document.querySelector('.game-page').classList.add('in-game');

  state.timer = setInterval(tick, 1000);
}

function renderBoard(cfg) {
  $board.style.gridTemplateColumns = `repeat(${cfg.cols}, 1fr)`;
  $board.innerHTML = '';

  state.cards.forEach((card, idx) => {
    const el = document.createElement('button');
    el.className = 'card';
    el.setAttribute('aria-label', '點擊翻牌');
    el.dataset.idx = idx;
    el.innerHTML = `
      <div class="card-inner">
        <div class="card-face card-back"><img class="card-back-img" src="../images/memory-match/card-back.jpg" alt="" onload="this.closest('.card-back').classList.add('has-img')" onerror="this.remove()"><span class="card-back-icon">🌸</span></div>
        <div class="card-face card-front">
          <span class="card-emoji">${card.emoji}</span>
        </div>
      </div>`;
    el.addEventListener('click', () => onCardClick(idx));
    $board.appendChild(el);
  });
}

function onCardClick(idx) {
  if (!state.active) return;
  if (state.locked) return;
  const card = state.cards[idx];
  if (card.flipped || card.matched) return;
  if (state.flipped.length >= 2) return;

  card.flipped = true;
  state.flipped.push(idx);
  $board.children[idx].classList.add('flipped');

  if (state.flipped.length === 2) {
    state.locked = true;
    setTimeout(evalPair, 1000);
  }
}

function evalPair() {
  const [i1, i2] = state.flipped;
  const c1 = state.cards[i1];
  const c2 = state.cards[i2];

  if (c1.emoji === c2.emoji) {
    c1.matched = c2.matched = true;
    $board.children[i1].classList.add('matched');
    $board.children[i2].classList.add('matched');
    state.matched++;
    $matched.textContent = state.matched;
    state.flipped = [];
    state.locked  = false;

    const cfg = DIFFICULTY[state.difficulty].levels[state.level - 1];
    if (state.matched === cfg.pairs) {
      setTimeout(onLevelDone, 400);
    }
  } else {
    $board.children[i1].classList.add('shake');
    $board.children[i2].classList.add('shake');
    setTimeout(() => {
      c1.flipped = c2.flipped = false;
      [$board.children[i1], $board.children[i2]].forEach(el => {
        el.classList.remove('flipped', 'shake');
      });
      state.flipped = [];
      state.locked  = false;
    }, 600);
  }
}

function tick() {
  state.timeLeft--;
  updateTimerDisplay();
  if (state.timeLeft <= 0) {
    clearInterval(state.timer);
    state.active = false;
    showResult(false);
  }
}

function onLevelDone() {
  clearInterval(state.timer);
  state.active = false;
  state.levelsCompleted++;
  const totalLevels = DIFFICULTY[state.difficulty].levels.length;
  if (state.level < totalLevels) {
    showDialog('level-clear');
  } else {
    showResult(true);
  }
}

// ─── Timer UI ─────────────────────────────────────────────────────────────────

function updateTimerDisplay() {
  $timer.textContent = state.timeLeft;
  $timer.className   = 'stat-value';
  if      (state.timeLeft <= 10) $timer.classList.add('danger');
  else if (state.timeLeft <= 20) $timer.classList.add('warn');
}

function updateDots(level) {
  for (let i = 1; i <= 3; i++) {
    const dot = document.getElementById(`dot-${i}`);
    dot.className = 'level-dot';
    if (i < level)  dot.classList.add('done');
    if (i === level) dot.classList.add('current');
  }
}

// ─── Dialog ───────────────────────────────────────────────────────────────────

function showDialog(type) {
  $dialog.classList.remove('hidden');

  const cfgs = {
    'level-clear': {
      emoji: '🎉',
      title: '太棒了！',
      msg: `第 ${state.level} 關完成！準備好迎戰下一關了嗎？`,
      btns: [
        { text: '繼續挑戰！→', cls: 'btn btn-primary btn-lg', fn: () => startLevel(state.level + 1) },
        { text: '回主選單',     cls: 'btn btn-outline',       fn: goHome },
      ],
    },
    'all-done': {
      emoji: '🏆',
      title: '全部完成！',
      msg: '恭喜！您挑戰了所有三關，腦力一等一！',
      btns: [
        { text: '🔁 再玩一次', cls: 'btn btn-primary btn-lg', fn: () => startLevel(1) },
        { text: '回主選單',    cls: 'btn btn-outline',        fn: goHome },
      ],
    },
    'timeout': {
      emoji: '⏰',
      title: '時間到了！',
      msg: `您已配對 ${state.matched} 對，繼續加油！`,
      btns: [
        { text: '🔁 重新挑戰', cls: 'btn btn-primary btn-lg', fn: () => startLevel(state.level) },
        { text: '回主選單',    cls: 'btn btn-outline',        fn: goHome },
      ],
    },
  };

  const cfg = cfgs[type];
  $dbEmoji.textContent = cfg.emoji;
  $dbTitle.textContent = cfg.title;
  $dbMsg.textContent   = cfg.msg;
  $dbBtns.innerHTML    = '';
  cfg.btns.forEach(b => {
    const btn = document.createElement('button');
    btn.className   = b.cls;
    btn.textContent = b.text;
    btn.addEventListener('click', b.fn);
    $dbBtns.appendChild(btn);
  });
}

// ─── Util ─────────────────────────────────────────────────────────────────────

function shuffle(arr) {
  for (let i = arr.length - 1; i > 0; i--) {
    const j = Math.floor(Math.random() * (i + 1));
    [arr[i], arr[j]] = [arr[j], arr[i]];
  }
  return arr;
}

function goHome() { location.href = '../index.html'; }

// ─── Score ────────────────────────────────────────────────────────────────────

function calcScore() {
  const diffBonus  = { easy: 0, normal: 100, hard: 200 };
  const totalLevels = DIFFICULTY[state.difficulty].levels.length;
  const totalTime   = DIFFICULTY[state.difficulty].totalTime;

  const completionPts = Math.round((state.levelsCompleted / totalLevels) * 500);
  const speedPts      = state.levelsCompleted === totalLevels
    ? Math.round((state.timeLeft / totalTime) * 300)
    : 0;
  const diffPts       = diffBonus[state.difficulty];

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

  document.getElementById('result-retry').onclick = () => startLevel(1);
  document.getElementById('result-home').onclick  = () => { location.href = '../index.html'; };

  $game.classList.add('hidden');
  $dialog.classList.add('hidden');
  $result.classList.remove('hidden');
  document.querySelector('.game-page').classList.add('showing-result');
}

// ─── Init ─────────────────────────────────────────────────────────────────────

['easy', 'normal', 'hard'].forEach(diff => {
  document.getElementById(`btn-${diff}`).addEventListener('click', () => startLevel(1, diff));
});
