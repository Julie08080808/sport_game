'use strict';

// ─── Animals ──────────────────────────────────────────────────────────────────
// Placement cells (% of scene width/height), split by terrain since only
// flying animals (bird, owl) may land in the sky — everyone else stays on the grass.

const SKY_CELLS = [
  { x: 6,  y: 7  },
  { x: 20, y: 6  },
  { x: 35, y: 13 },
  { x: 50, y: 7  },
  { x: 65, y: 15 },
  { x: 80, y: 6  },
  { x: 94, y: 17 },
  { x: 15, y: 24 },
  { x: 46, y: 22 },
  { x: 77, y: 25 },
];
const GROUND_CELLS = [
  { x: 8,  y: 33 },
  { x: 25, y: 29 },
  { x: 42, y: 36 },
  { x: 58, y: 31 },
  { x: 74, y: 38 },
  { x: 91, y: 33 },
  { x: 12, y: 55 },
  { x: 30, y: 58 },
  { x: 50, y: 60 },
  { x: 68, y: 56 },
  { x: 87, y: 60 },
  { x: 18, y: 79 },
  { x: 40, y: 83 },
  { x: 62, y: 80 },
  { x: 83, y: 76 },
];

// Animal ids allowed to be placed in the sky. The target bird is handled
// separately in spawnRound and can land anywhere (sky or ground).
const SKY_ALLOWED = new Set(['owl', 'owl2']);

const ALL_ANIMALS = [
  { id: 'bird',    img: '../images/find-bird/bird.png',                 isTarget: true },
  { id: 'rabbit',  img: '../images/find-bird/rabbit-farmer.png' },
  { id: 'beaver',  img: '../images/find-bird/beaver-bear.png' },
  { id: 'fox',     img: '../images/find-bird/fox-chef.png' },
  { id: 'monkey',  img: '../images/find-bird/mountain-monkey.png' },
  { id: 'owl',     img: '../images/find-bird/owl-scholar.png' },
  { id: 'dog',     img: '../images/find-bird/dog-merchant.png' },
  { id: 'rabbit2', img: '../images/find-bird/rabbit-farmer-blue.png' },
  { id: 'beaver2', img: '../images/find-bird/beaver-bear-purple.png' },
  { id: 'fox2',    img: '../images/find-bird/fox-chef-pink.png' },
  { id: 'monkey2', img: '../images/find-bird/mountain-monkey-red.png' },
  { id: 'owl2',    img: '../images/find-bird/owl-scholar-teal.png' },
  { id: 'dog2',    img: '../images/find-bird/dog-merchant-green.png' },
  { id: 'rabbit3', img: '../images/find-bird/rabbit-farmer-green.png' },
  { id: 'fox3',    img: '../images/find-bird/fox-chef-purple.png' },
  { id: 'monkey3', img: '../images/find-bird/mountain-monkey-blue.png' },
];
const TARGET = ALL_ANIMALS.find(a => a.isTarget);
const DECOYS = ALL_ANIMALS.filter(a => !a.isTarget);

// ─── Config ───────────────────────────────────────────────────────────────────

const DIFFICULTY = {
  easy: {
    label: '簡單', cssClass: 'easy',
    animalCount: 8, spriteSize: 76,
    findTime: 10, findsTotal: 5,
  },
  normal: {
    label: '普通', cssClass: 'normal',
    animalCount: 12, spriteSize: 76,
    findTime: 6, findsTotal: 5,
  },
  hard: {
    label: '困難', cssClass: 'hard',
    animalCount: 16, spriteSize: 76,
    findTime: 3, findsTotal: 5,
  },
};

// ─── State ────────────────────────────────────────────────────────────────────

let state = {
  difficulty:    'normal',
  finds:         0,
  timeLeft:      60,
  totalSeconds:  0,
  findStartTime: 0,
  roundStartTime:0,
  rafId:         null,
  active:        false,
};

// ─── DOM ──────────────────────────────────────────────────────────────────────

const $start      = document.getElementById('start-screen');
const $game       = document.getElementById('game-screen');
const $result     = document.getElementById('result-screen');
const $scene      = document.getElementById('bird-scene');
const $timer      = document.getElementById('timer-value');
const $findsCount = document.getElementById('finds-count');
const $findsNeeded= document.getElementById('finds-needed');
const $findsBar   = document.getElementById('finds-bar');
const $timeBarFill= document.getElementById('time-bar-fill');
const $diffBadge  = document.getElementById('diff-badge');
const $hintText   = document.getElementById('hint-text');

// ─── Game Start ───────────────────────────────────────────────────────────────

function startGame(diff) {
  if (diff !== undefined) state.difficulty = diff;
  const cfg = DIFFICULTY[state.difficulty];

  $diffBadge.textContent = cfg.label;
  $diffBadge.className   = 'diff-badge ' + cfg.cssClass;

  $start.classList.add('hidden');
  $result.classList.add('hidden');
  $game.classList.remove('hidden');
  document.querySelector('.game-page').classList.add('in-game');

  loadRound();
}

// ─── Load Round ──────────────────────────────────────────────────────────────

function loadRound() {
  const cfg = DIFFICULTY[state.difficulty];
  const now = performance.now();
  state.finds          = 0;
  state.timeLeft       = cfg.findTime;
  state.totalSeconds   = 0;
  state.findStartTime  = now;
  state.roundStartTime = now;
  state.active         = true;

  $findsNeeded.textContent = cfg.findsTotal;
  $findsCount.textContent  = 0;

  // Rebuild find dots
  $findsBar.innerHTML = '';
  for (let i = 0; i < cfg.findsTotal; i++) {
    const dot = document.createElement('div');
    dot.className = 'find-dot';
    dot.id = `fdot-${i}`;
    $findsBar.appendChild(dot);
  }

  $hintText.textContent = '';

  cancelAnimationFrame(state.rafId);
  state.rafId = requestAnimationFrame(timerLoop);

  spawnRound();
}

// ─── Timer ───────────────────────────────────────────────────────────────────
// Driven by requestAnimationFrame + real elapsed time (instead of setInterval)
// so the countdown never drifts or stutters under load.

function timerLoop(now) {
  if (!state.active) return;

  const cfg       = DIFFICULTY[state.difficulty];
  const elapsed   = (now - state.findStartTime) / 1000;
  const remaining = Math.max(0, cfg.findTime - elapsed);

  state.timeLeft     = Math.ceil(remaining);
  state.totalSeconds = (now - state.roundStartTime) / 1000;
  updateTimerDisplay(remaining);

  if (remaining <= 0) {
    state.active = false;
    showResult(false);
    return;
  }

  state.rafId = requestAnimationFrame(timerLoop);
}

function updateTimerDisplay(remaining) {
  const cfg = DIFFICULTY[state.difficulty];
  if (remaining === undefined) remaining = state.timeLeft;

  if ($timer.textContent !== String(state.timeLeft)) {
    $timer.textContent = state.timeLeft;
  }

  const pct = Math.max(0, remaining / cfg.findTime * 100);
  // Use a transform, not width, so the browser can animate this on the
  // compositor every frame without forcing a layout recalc each time.
  $timeBarFill.style.transform = `scaleX(${pct / 100})`;
}

// ─── Round Spawn ─────────────────────────────────────────────────────────────

function shuffle(arr) {
  for (let i = arr.length - 1; i > 0; i--) {
    const j = Math.floor(Math.random() * (i + 1));
    [arr[i], arr[j]] = [arr[j], arr[i]];
  }
  return arr;
}

function spawnRound() {
  if (!state.active) return;
  $scene.innerHTML = '';

  const cfg = DIFFICULTY[state.difficulty];
  const decoys = shuffle(DECOYS.slice()).slice(0, cfg.animalCount - 1);
  const round = shuffle([TARGET, ...decoys]);

  // Ground-bound animals must land on grass; owls may use either. The target
  // bird draws FIRST from the full combined pool (all sky + ground cells),
  // giving it an equal shot at any spot in the scene — picking it from
  // whatever happens to be left over (after ground/sky animals are placed)
  // skews it toward the sky, since the 10 sky cells are rarely touched by
  // other animals while the ground pool gets used up fast.
  const allCells  = shuffle([...GROUND_CELLS, ...SKY_CELLS]);
  const birdCell  = allCells[0];
  const restCells = allCells.slice(1);
  const restGroundCells = restCells.filter(c => GROUND_CELLS.includes(c));
  const restSkyCells    = restCells.filter(c => SKY_CELLS.includes(c));

  const groundAnimals = round.filter(a => !a.isTarget && !SKY_ALLOWED.has(a.id));
  const skyAnimals    = round.filter(a => !a.isTarget &&  SKY_ALLOWED.has(a.id));

  const usedGround     = restGroundCells.slice(0, groundAnimals.length);
  const leftoverGround = restGroundCells.slice(groundAnimals.length);
  const skyPool        = shuffle([...restSkyCells, ...leftoverGround]);
  const usedSky        = skyPool.slice(0, skyAnimals.length);

  const placements = [
    ...groundAnimals.map((animal, i) => ({ animal, cell: usedGround[i] })),
    ...skyAnimals.map((animal, i) => ({ animal, cell: usedSky[i] })),
    { animal: TARGET, cell: birdCell },
  ];

  // Keep every sprite fully inside the scene box — cell % come from fixed
  // layout constants, but the box's rendered size and the sprite's pixel
  // size both vary (device width, difficulty), so clamp against the box's
  // actual measured size instead of trusting the raw percentages.
  const sceneRect  = $scene.getBoundingClientRect();
  const marginXPct = Math.min(45, (cfg.spriteSize / 2 / sceneRect.width)  * 100);
  const marginYPct = Math.min(45, (cfg.spriteSize / 2 / sceneRect.height) * 100);

  placements.forEach(({ animal, cell }) => {
    const el = document.createElement('img');
    el.className = 'animal-el appear' +
      (state.difficulty === 'easy' && animal.isTarget ? ' easy-glow' : '');
    el.src   = animal.img;
    el.alt   = '';
    el.style.left  = Math.min(100 - marginXPct, Math.max(marginXPct, cell.x)) + '%';
    el.style.top   = Math.min(100 - marginYPct, Math.max(marginYPct, cell.y)) + '%';
    el.style.width = cfg.spriteSize + 'px';
    el.addEventListener('click', () => onAnimalClick(el, animal));
    $scene.appendChild(el);
  });
}

// ─── Animal Click ────────────────────────────────────────────────────────────

function onAnimalClick(el, animal) {
  if (!state.active) return;
  if (animal.isTarget) {
    onFound(el);
  } else {
    onWrongPick(el);
  }
}

function onWrongPick(el) {
  el.classList.remove('wrong-pick');
  void el.offsetWidth; // restart animation
  el.classList.add('wrong-pick');
  $hintText.textContent = '🤔 不是牠喔，再找找看！';
}

function onFound(el) {
  // Lock this round's sprites against further clicks
  Array.from($scene.children).forEach(c => c.style.pointerEvents = 'none');
  el.classList.add('caught');

  // Sparkle effect at the found position
  const sparkle = document.createElement('div');
  sparkle.textContent = '✨';
  sparkle.style.cssText = `
    position:absolute;
    left:${el.style.left};
    top:${el.style.top};
    font-size:34px;
    z-index:20;
    pointer-events:none;
    transform:translate(-50%,-50%);
    animation:sparkleOut .6s ease-out forwards;
  `;
  $scene.appendChild(sparkle);
  setTimeout(() => sparkle.remove(), 620);

  state.finds++;
  $findsCount.textContent = state.finds;

  const dot = document.getElementById(`fdot-${state.finds - 1}`);
  if (dot) dot.classList.add('found');

  $hintText.textContent = '🎉 找到了！太棒了！';

  const cfg    = DIFFICULTY[state.difficulty];
  const isLast = state.finds >= cfg.findsTotal;

  // Refill the per-bird countdown the instant the bird is caught, rather
  // than waiting for the next round's animals to finish spawning.
  if (!isLast) {
    state.findStartTime = performance.now();
    state.timeLeft      = cfg.findTime;
    updateTimerDisplay(cfg.findTime);
  }

  setTimeout(() => {
    if (!state.active) return;
    if (isLast) {
      state.active = false;
      showResult(true);
    } else {
      spawnRound();
    }
  }, 500);
}

// ─── Score ────────────────────────────────────────────────────────────────────

function calcScore() {
  const diffBonus   = { easy: 0, normal: 100, hard: 200 };
  const cfg         = DIFFICULTY[state.difficulty];
  const totalNeeded = cfg.findsTotal;
  const totalTime   = cfg.findTime * cfg.findsTotal;

  const completionPts = Math.round((state.finds / totalNeeded) * 500);
  const speedPts      = Math.max(0, Math.round(300 * (1 - state.totalSeconds / totalTime)));
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
  cancelAnimationFrame(state.rafId);
  state.active = false;
  $scene.innerHTML = '';

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
  const t0     = performance.now();
  (function animate(now) {
    const p = Math.min((now - t0) / 1200, 1);
    scoreEl.textContent = Math.round(target * (1 - Math.pow(1 - p, 3)));
    if (p < 1) requestAnimationFrame(animate);
  })(t0);

  document.getElementById('result-retry').onclick = () => startGame();
  document.getElementById('result-home').onclick  = () => { location.href = '../index.html'; };

  $game.classList.add('hidden');
  $result.classList.remove('hidden');
  document.querySelector('.game-page').classList.add('showing-result');
}

// ─── Init ─────────────────────────────────────────────────────────────────────

['easy', 'normal', 'hard'].forEach(diff => {
  document.getElementById(`btn-${diff}`).addEventListener('click', () => startGame(diff));
});
