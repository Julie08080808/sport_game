'use strict';

// ─── Question Banks ───────────────────────────────────────────────────────────

const QUESTIONS_EASY = [
  {
    id: 1, stage: 1, stageLabel: '🔢 加法計算',
    context: '您在飲料店點餐',
    items: [
      { emoji: '🍵', name: '松果茶', price: 30 },
      { emoji: '🍠', name: '地瓜餅', price: 20 },
    ],
    paid: null,
    qText: '請問總共要付多少錢？',
    answer: 50, wrong: 40,
  },
  {
    id: 2, stage: 1, stageLabel: '🔢 加法計算',
    context: '您在傳統市場買菜',
    items: [
      { emoji: '🥬', name: '青菜', price: 25 },
      { emoji: '🧊', name: '豆腐', price: 15 },
    ],
    paid: null,
    qText: '請問總共要付多少錢？',
    answer: 40, wrong: 30,
  },
  {
    id: 3, stage: 1, stageLabel: '🔢 加法計算',
    context: '熊熊在麵包店買早餐',
    items: [
      { emoji: '🐻', name: '熊熊麵包', price: 40 },
      { emoji: '🥛', name: '牛奶',   price: 50 },
    ],
    paid: null,
    qText: '請問總共要付多少錢？',
    answer: 90, wrong: 80,
  },
  {
    id: 4, stage: 1, stageLabel: '🔢 加法計算',
    context: '您到超市買早餐材料',
    items: [
      { emoji: '🥣', name: '燕麥片', price: 60 },
      { emoji: '🥤', name: '豆漿',   price: 30 },
    ],
    paid: null,
    qText: '請問總共要付多少錢？',
    answer: 90, wrong: 80,
  },
  {
    id: 5, stage: 1, stageLabel: '🔢 加法計算',
    context: '兔子在健康餐廳點餐',
    items: [
      { emoji: '🧃', name: '紅蘿蔔汁', price: 45 },
      { emoji: '🥗', name: '沙拉',   price: 40 },
    ],
    paid: null,
    qText: '請問總共要付多少錢？',
    answer: 85, wrong: 75,
  },
  {
    id: 6, stage: 1, stageLabel: '🔢 加法計算',
    context: '您在水果攤買水果',
    items: [
      { emoji: '🍎', name: '蘋果一袋', price: 100 },
      { emoji: '🍌', name: '香蕉',   price: 50 },
    ],
    paid: null,
    qText: '請問總共要付多少錢？',
    answer: 150, wrong: 140,
  },
  {
    id: 7, stage: 1, stageLabel: '🔢 加法計算',
    context: '您在雜貨店買調味料',
    items: [
      { emoji: '🥚', name: '雞蛋',   price: 65 },
      { emoji: '🧂', name: '一包鹽', price: 15 },
    ],
    paid: null,
    qText: '請問總共要付多少錢？',
    answer: 80, wrong: 70,
  },
  {
    id: 8, stage: 1, stageLabel: '🔢 加法計算',
    context: '您在餐廳點了套餐',
    items: [
      { emoji: '🍲', name: '南瓜湯',   price: 55 },
      { emoji: '🥖', name: '香蒜麵包', price: 25 },
    ],
    paid: null,
    qText: '請問總共要付多少錢？',
    answer: 80, wrong: 70,
  },
  {
    id: 9, stage: 1, stageLabel: '🔢 加法計算',
    context: '貓咪在餐廳點餐',
    items: [
      { emoji: '🐟', name: '烤魚', price: 70 },
      { emoji: '🍚', name: '白飯', price: 15 },
    ],
    paid: null,
    qText: '請問總共要付多少錢？',
    answer: 85, wrong: 75,
  },
  {
    id: 10, stage: 1, stageLabel: '🔢 加法計算',
    context: '您在藥局買防疫用品',
    items: [
      { emoji: '😷', name: '口罩',   price: 80 },
      { emoji: '🧻', name: '濕紙巾', price: 20 },
    ],
    paid: null,
    qText: '請問總共要付多少錢？',
    answer: 100, wrong: 90,
  },
  {
    id: 11, stage: 1, stageLabel: '🔢 加法計算',
    context: '您在小吃攤買豆花',
    items: [
      { emoji: '🍮', name: '熱豆花', price: 40 },
      { emoji: '🫘', name: '紅豆',   price: 10 },
    ],
    paid: null,
    qText: '請問總共要付多少錢？',
    answer: 50, wrong: 60,
  },
  {
    id: 12, stage: 1, stageLabel: '🔢 加法計算',
    context: '您在早餐店買早餐',
    items: [
      { emoji: '🥛', name: '溫鮮奶', price: 35 },
      { emoji: '🍞', name: '饅頭',   price: 15 },
    ],
    paid: null,
    qText: '請問總共要付多少錢？',
    answer: 50, wrong: 40,
  },
  {
    id: 13, stage: 1, stageLabel: '🔢 加法計算',
    context: '您在自助餐店買午餐',
    items: [
      { emoji: '🥦', name: '炒青菜', price: 50 },
      { emoji: '🍱', name: '滷肉飯', price: 30 },
    ],
    paid: null,
    qText: '請問總共要付多少錢？',
    answer: 80, wrong: 70,
  },
  {
    id: 14, stage: 1, stageLabel: '🔢 加法計算',
    context: '您在雜貨店買調味料',
    items: [
      { emoji: '🍶', name: '醬油',   price: 85 },
      { emoji: '🍬', name: '一包糖', price: 35 },
    ],
    paid: null,
    qText: '請問總共要付多少錢？',
    answer: 120, wrong: 110,
  },
  {
    id: 15, stage: 1, stageLabel: '🔢 加法計算',
    context: '您在下午茶店點餐',
    items: [
      { emoji: '🍰', name: '海綿蛋糕', price: 60 },
      { emoji: '🍵', name: '熱茶',   price: 40 },
    ],
    paid: null,
    qText: '請問總共要付多少錢？',
    answer: 100, wrong: 90,
  },
  {
    id: 16, stage: 1, stageLabel: '🔢 加法計算',
    context: '小狗在餐廳點餐',
    items: [
      { emoji: '🍲', name: '肉骨茶', price: 90 },
      { emoji: '🍚', name: '白飯',   price: 20 },
    ],
    paid: null,
    qText: '請問總共要付多少錢？',
    answer: 110, wrong: 100,
  },
  {
    id: 17, stage: 1, stageLabel: '🔢 加法計算',
    context: '您在超市買點心',
    items: [
      { emoji: '🍪', name: '營養餅乾', price: 75 },
      { emoji: '🥛', name: '保久乳',   price: 25 },
    ],
    paid: null,
    qText: '請問總共要付多少錢？',
    answer: 100, wrong: 90,
  },
  {
    id: 18, stage: 1, stageLabel: '🔢 加法計算',
    context: '您在早餐店買早餐',
    items: [
      { emoji: '🍘', name: '蘿蔔糕', price: 35 },
      { emoji: '🥤', name: '豆漿',   price: 20 },
    ],
    paid: null,
    qText: '請問總共要付多少錢？',
    answer: 55, wrong: 45,
  },
  {
    id: 19, stage: 1, stageLabel: '🔢 加法計算',
    context: '您在水果攤買水果',
    items: [
      { emoji: '🍊', name: '橘子', price: 80 },
      { emoji: '🍎', name: '蘋果', price: 25 },
    ],
    paid: null,
    qText: '請問總共要付多少錢？',
    answer: 105, wrong: 95,
  },
  {
    id: 20, stage: 1, stageLabel: '🔢 加法計算',
    context: '您在藥局買日用品',
    items: [
      { emoji: '💧', name: '老花眼藥水', price: 120 },
      { emoji: '🧼', name: '棉花棒',   price: 30 },
    ],
    paid: null,
    qText: '請問總共要付多少錢？',
    answer: 150, wrong: 140,
  },
];

const QUESTIONS_NORMAL = [
  {
    id: 1, stage: 2, stageLabel: '💴 找零錢',
    context: '您在小吃攤買粥品',
    items: [ { emoji: '🍲', name: '香菇粥', price: 60 } ],
    paid: 100,
    qText: '請問店員要找回您多少錢？',
    answer: 40, wrong: 50,
  },
  {
    id: 2, stage: 2, stageLabel: '💴 找零錢',
    context: '您在藥局買保健品',
    items: [ { emoji: '💊', name: '維他命', price: 350 } ],
    paid: 500,
    qText: '請問店員要找回您多少錢？',
    answer: 150, wrong: 160,
  },
  {
    id: 3, stage: 2, stageLabel: '💴 找零錢',
    context: '您在水果攤買水果盤',
    items: [ { emoji: '🍉', name: '水果盤', price: 120 } ],
    paid: 200,
    qText: '請問店員要找回您多少錢？',
    answer: 80, wrong: 90,
  },
  {
    id: 4, stage: 2, stageLabel: '💴 找零錢',
    context: '您在藥局買藥膏',
    items: [ { emoji: '💊', name: '舒緩藥膏', price: 180 } ],
    paid: 500,
    qText: '請問店員要找回您多少錢？',
    answer: 320, wrong: 330,
  },
  {
    id: 5, stage: 2, stageLabel: '💰 折扣計算',
    context: '您在點心店買橡果餅乾',
    items: [ { emoji: '🍪', name: '橡果餅乾', price: 150 } ],
    paid: null,
    qText: '特價折 30 元，請問實際要付多少錢？',
    answer: 120, wrong: 130,
  },
  {
    id: 6, stage: 2, stageLabel: '💴 找零錢',
    context: '您在傳統市場買青蔥',
    items: [ { emoji: '🌱', name: '青蔥', price: 35 } ],
    paid: 50,
    qText: '請問店員要找回您多少錢？',
    answer: 15, wrong: 25,
  },
  {
    id: 7, stage: 2, stageLabel: '💴 找零錢',
    context: '貓咪在餐廳點餐',
    items: [ { emoji: '🐟', name: '鮮魚餐', price: 220 } ],
    paid: 500,
    qText: '請問店員要找回您多少錢？',
    answer: 280, wrong: 270,
  },
  {
    id: 8, stage: 2, stageLabel: '💴 找零錢',
    context: '您在乾果店買核桃',
    items: [ { emoji: '🌰', name: '核桃', price: 190 } ],
    paid: 1000,
    qText: '請問店員要找回您多少錢？',
    answer: 810, wrong: 800,
  },
  {
    id: 9, stage: 2, stageLabel: '💴 找零錢',
    context: '您在雜貨店買肉鬆',
    items: [ { emoji: '🍖', name: '肉鬆', price: 260 } ],
    paid: 500,
    qText: '請問店員要找回您多少錢？',
    answer: 240, wrong: 250,
  },
  {
    id: 10, stage: 2, stageLabel: '💴 找零錢',
    context: '您在中藥行買人參茶包',
    items: [ { emoji: '🍵', name: '人參茶包', price: 450 } ],
    paid: 1000,
    qText: '請問店員要找回您多少錢？',
    answer: 550, wrong: 560,
  },
  {
    id: 11, stage: 2, stageLabel: '💴 找零錢',
    context: '您在小吃攤買麵線',
    items: [ { emoji: '🍜', name: '素麵線', price: 45 } ],
    paid: 100,
    qText: '請問店員要找回您多少錢？',
    answer: 55, wrong: 65,
  },
  {
    id: 12, stage: 2, stageLabel: '💴 找零錢',
    context: '您在傳統市場買高麗菜',
    items: [ { emoji: '🥬', name: '高麗菜', price: 85 } ],
    paid: 100,
    qText: '請問店員要找回您多少錢？',
    answer: 15, wrong: 25,
  },
  {
    id: 13, stage: 2, stageLabel: '💴 找零錢',
    context: '您在服飾店買保暖背心',
    items: [ { emoji: '🧥', name: '保暖背心', price: 390 } ],
    paid: 500,
    qText: '請問店員要找回您多少錢？',
    answer: 110, wrong: 100,
  },
  {
    id: 14, stage: 2, stageLabel: '💴 找零錢',
    context: '小熊在雜貨店買蜂蜜',
    items: [ { emoji: '🍯', name: '蜂蜜', price: 280 } ],
    paid: 500,
    qText: '請問店員要找回您多少錢？',
    answer: 220, wrong: 210,
  },
  {
    id: 15, stage: 2, stageLabel: '💴 找零錢',
    context: '您在超市買燕麥片',
    items: [ { emoji: '🥣', name: '大燕麥片', price: 130 } ],
    paid: 200,
    qText: '請問店員要找回您多少錢？',
    answer: 70, wrong: 60,
  },
  {
    id: 16, stage: 2, stageLabel: '💴 找零錢',
    context: '您在百貨行買雨傘',
    items: [ { emoji: '☂️', name: '雨傘', price: 150 } ],
    paid: 500,
    qText: '請問店員要找回您多少錢？',
    answer: 350, wrong: 340,
  },
  {
    id: 17, stage: 2, stageLabel: '💴 找零錢',
    context: '您在藥局買鈣片',
    items: [ { emoji: '💊', name: '鈣片', price: 600 } ],
    paid: 1000,
    qText: '請問店員要找回您多少錢？',
    answer: 400, wrong: 390,
  },
  {
    id: 18, stage: 2, stageLabel: '💰 折扣計算',
    context: '您在餐廳點了清蒸魚',
    items: [ { emoji: '🐟', name: '清蒸魚', price: 160 } ],
    paid: null,
    qText: '特價折 20 元，請問實際要付多少錢？',
    answer: 140, wrong: 150,
  },
  {
    id: 19, stage: 2, stageLabel: '💴 找零錢',
    context: '您在雜貨店買白米',
    items: [ { emoji: '🍚', name: '白米', price: 240 } ],
    paid: 500,
    qText: '請問店員要找回您多少錢？',
    answer: 260, wrong: 270,
  },
  {
    id: 20, stage: 2, stageLabel: '💴 找零錢',
    context: '您在生活用品店買防滑拖鞋',
    items: [ { emoji: '🩴', name: '防滑拖鞋', price: 120 } ],
    paid: 500,
    qText: '請問店員要找回您多少錢？',
    answer: 380, wrong: 370,
  },
  {
    id: 21, stage: 2, stageLabel: '🐔 雞兔同籠',
    context: '院子裡有雞和兔子',
    items: [
      { emoji: '🐔', name: '雞',   price: 2, priceUnit: '隻腳', qty: 3, unit: '隻' },
      { emoji: '🐰', name: '兔子', price: 4, priceUnit: '隻腳', qty: 1, unit: '隻' },
    ],
    paid: null,
    qText: '請問雞和兔子總共有幾隻腳？',
    answer: 10, wrong: 8, answerUnit: '隻腳',
  },
  {
    id: 22, stage: 2, stageLabel: '💰 折扣計算',
    context: '您在超商買飯糰，一顆 35 元，現在加 10 元就能再多一顆',
    items: [ { emoji: '🍙', name: '飯糰', price: 35, qty: 1, unit: '顆' } ],
    paid: null,
    qText: '如果您想要兩顆飯糰，總共要付多少錢？',
    answer: 45, wrong: 70,
  },
];

const QUESTIONS_HARD = [
  {
    id: 1, stage: 3, stageLabel: '✖ 乘法應用',
    context: '您在點心攤買堅果塔',
    items: [ { emoji: '🥜', name: '堅果塔', price: 40, qty: 3, unit: '個' } ],
    paid: null,
    qText: '請問總共要付多少錢？',
    answer: 120, wrong: 110,
  },
  {
    id: 2, stage: 3, stageLabel: '✖ 乘法應用',
    context: '您在雜貨店買雞蛋',
    items: [ { emoji: '🥚', name: '雞蛋', price: 60, qty: 2, unit: '盒' } ],
    paid: null,
    qText: '請問總共要付多少錢？',
    answer: 120, wrong: 110,
  },
  {
    id: 3, stage: 3, stageLabel: '✖ 乘法應用',
    context: '您在傳統市場買青菜',
    items: [ { emoji: '🥬', name: '青菜', price: 25, qty: 3, unit: '把' } ],
    paid: null,
    qText: '請問總共要付多少錢？',
    answer: 75, wrong: 65,
  },
  {
    id: 4, stage: 3, stageLabel: '✖ 乘法應用',
    context: '您在超市買罐頭',
    items: [ { emoji: '🥫', name: '鮪魚罐頭', price: 45, qty: 2, unit: '罐' } ],
    paid: null,
    qText: '請問總共要付多少錢？',
    answer: 90, wrong: 80,
  },
  {
    id: 5, stage: 3, stageLabel: '✖ 乘法應用',
    context: '您在點心攤買餅乾',
    items: [ { emoji: '🍪', name: '貓咪餅乾', price: 20, qty: 5, unit: '片' } ],
    paid: null,
    qText: '請問總共要付多少錢？',
    answer: 100, wrong: 90,
  },
  {
    id: 6, stage: 3, stageLabel: '✖ 乘法應用',
    context: '您在超市買豆漿',
    items: [ { emoji: '🥤', name: '豆漿', price: 25, qty: 4, unit: '瓶' } ],
    paid: null,
    qText: '請問總共要付多少錢？',
    answer: 100, wrong: 90,
  },
  {
    id: 7, stage: 3, stageLabel: '✖ 乘法應用',
    context: '您在菜攤買地瓜，付了 100 元',
    items: [ { emoji: '🍠', name: '地瓜', price: 35, qty: 2, unit: '條' } ],
    paid: 100,
    qText: '請問店員要找回您多少錢？',
    answer: 30, wrong: 20,
  },
  {
    id: 8, stage: 3, stageLabel: '✖ 乘法應用',
    context: '您在水果攤買蘋果',
    items: [
      { emoji: '🍎', name: '蘋果', price: 20, qty: 3, unit: '顆' },
      { emoji: '🛍️', name: '提袋', price: 2 },
    ],
    paid: null,
    qText: '買了 3 顆蘋果再加一個提袋，請問總共要付多少錢？',
    answer: 62, wrong: 52,
  },
  {
    id: 9, stage: 3, stageLabel: '✖ 乘法應用',
    context: '您在超市買保久乳',
    items: [ { emoji: '🥛', name: '保久乳', price: 30, qty: 2, unit: '瓶' } ],
    paid: null,
    qText: '買了 2 瓶保久乳，特價共折 10 元，請問實際要付多少錢？',
    answer: 50, wrong: 40,
  },
  {
    id: 10, stage: 3, stageLabel: '✖ 乘法應用',
    context: '您在自助餐店買午餐',
    items: [
      { emoji: '🍚', name: '白飯', price: 15, qty: 3, unit: '碗' },
      { emoji: '🥗', name: '小菜', price: 30 },
    ],
    paid: null,
    qText: '買了 3 碗白飯再加小菜，請問總共要付多少錢？',
    answer: 75, wrong: 65,
  },
  {
    id: 11, stage: 3, stageLabel: '✖ 乘法應用',
    context: '兔子在甜點店點餐',
    items: [ { emoji: '🥕', name: '紅蘿蔔蛋糕', price: 55, qty: 2, unit: '份' } ],
    paid: null,
    qText: '請問總共要付多少錢？',
    answer: 110, wrong: 100,
  },
  {
    id: 12, stage: 3, stageLabel: '✖ 乘法應用',
    context: '您在服飾店買保暖用品',
    items: [ { emoji: '🧦', name: '保暖襪', price: 50, qty: 5, unit: '雙' } ],
    paid: null,
    qText: '請問總共要付多少錢？',
    answer: 250, wrong: 240,
  },
  {
    id: 13, stage: 3, stageLabel: '✖ 乘法應用',
    context: '您在日用品店買衛生紙',
    items: [ { emoji: '🧻', name: '衛生紙', price: 120, qty: 2, unit: '包' } ],
    paid: null,
    qText: '請問總共要付多少錢？',
    answer: 240, wrong: 230,
  },
  {
    id: 14, stage: 3, stageLabel: '✖ 乘法應用',
    context: '您在雜貨店買花生麵筋，付了 200 元',
    items: [ { emoji: '🥫', name: '花生麵筋', price: 40, qty: 3, unit: '罐' } ],
    paid: 200,
    qText: '請問店員要找回您多少錢？',
    answer: 80, wrong: 70,
  },
  {
    id: 15, stage: 3, stageLabel: '✖ 乘法應用',
    context: '您在滷味攤買茶葉蛋',
    items: [ { emoji: '🥚', name: '茶葉蛋', price: 15, qty: 4, unit: '顆' } ],
    paid: null,
    qText: '請問總共要付多少錢？',
    answer: 60, wrong: 50,
  },
  {
    id: 16, stage: 3, stageLabel: '✖ 乘法應用',
    context: '您在超市買餅乾',
    items: [ { emoji: '🍪', name: '燕麥餅乾', price: 80, qty: 2, unit: '包' } ],
    paid: null,
    qText: '買了 2 包燕麥餅乾，特價共折 20 元，請問實際要付多少錢？',
    answer: 140, wrong: 130,
  },
  {
    id: 17, stage: 3, stageLabel: '✖ 乘法應用',
    context: '您在便利商店買飲料',
    items: [
      { emoji: '💧', name: '礦泉水', price: 20, qty: 3, unit: '瓶' },
      { emoji: '🍬', name: '糖果', price: 40 },
    ],
    paid: null,
    qText: '買了 3 瓶礦泉水再加糖果，請問總共要付多少錢？',
    answer: 100, wrong: 90,
  },
  {
    id: 18, stage: 3, stageLabel: '✖ 乘法應用',
    context: '您在魚攤買鮮魚',
    items: [ { emoji: '🐟', name: '鮮魚', price: 150, qty: 2, unit: '條' } ],
    paid: null,
    qText: '請問總共要付多少錢？',
    answer: 300, wrong: 290,
  },
  {
    id: 19, stage: 3, stageLabel: '✖ 乘法應用',
    context: '您在水果攤買橘子',
    items: [ { emoji: '🍊', name: '橘子', price: 12, qty: 5, unit: '顆' } ],
    paid: null,
    qText: '請問總共要付多少錢？',
    answer: 60, wrong: 50,
  },
  {
    id: 20, stage: 3, stageLabel: '✖ 乘法應用',
    context: '小狗在餐廳點餐',
    items: [ { emoji: '🦴', name: '特製肉骨頭', price: 70, qty: 3, unit: '根' } ],
    paid: null,
    qText: '請問總共要付多少錢？',
    answer: 210, wrong: 200,
  },
  {
    id: 21, stage: 3, stageLabel: '🐔 雞兔同籠',
    context: '農場裡有雞和兔子',
    items: [
      { emoji: '🐔', name: '雞',   price: 2, priceUnit: '隻腳', qty: 3, unit: '隻' },
      { emoji: '🐰', name: '兔子', price: 4, priceUnit: '隻腳', qty: 2, unit: '隻' },
    ],
    paid: null,
    qText: '請問雞和兔子總共有幾隻腳？',
    answer: 14, wrong: 10, answerUnit: '隻腳',
  },
  {
    id: 22, stage: 3, stageLabel: '🐔 雞兔同籠',
    context: '鄰居家的雞舍裡有雞和兔子',
    items: [
      { emoji: '🐔', name: '雞',   price: 2, priceUnit: '隻腳', qty: 4, unit: '隻' },
      { emoji: '🐰', name: '兔子', price: 4, priceUnit: '隻腳', qty: 3, unit: '隻' },
    ],
    paid: null,
    qText: '請問雞和兔子總共有幾隻腳？',
    answer: 20, wrong: 14, answerUnit: '隻腳',
  },
  {
    id: 23, stage: 3, stageLabel: '🛒 精打細算',
    context: '舒潔衛生紙特價比較：好市多 120 抽賣 99 元、全聯 110 抽賣 89 元、雙十一特價出了一款 100 抽原價 80 元，現在打 88 折',
    items: [
      { emoji: '🏬', name: '好市多', price: 99, qty: 120, unit: '抽' },
      { emoji: '🏪', name: '全聯',   price: 89, qty: 110, unit: '抽' },
      { emoji: '🎉', name: '雙十一', price: 70, qty: 100, unit: '抽' },
    ],
    paid: null,
    qText: '請問哪一款衛生紙比較划算？',
    options: [
      { label: 'A 好市多', correct: false },
      { label: 'B 全聯',   correct: false },
      { label: 'C 雙十一', correct: true  },
    ],
  },
  {
    id: 24, stage: 3, stageLabel: '🛒 精打細算',
    context: '服飾店特價方案比較：方案 A「每件七五折」、方案 B「買一件、第二件六折」',
    items: [],
    paid: null,
    qText: '如果要買兩件一樣的衣服，請問哪一種方案比較划算？',
    options: [
      { label: 'A 每件七五折', correct: true  },
      { label: 'B 第二件六折', correct: false },
    ],
  },
];

const DIFFICULTY = {
  easy:   { label: '簡單', cssClass: 'easy',   questions: QUESTIONS_EASY   },
  normal: { label: '普通', cssClass: 'normal', questions: QUESTIONS_NORMAL },
  hard:   { label: '困難', cssClass: 'hard',   questions: QUESTIONS_HARD   },
};

// ─── State ────────────────────────────────────────────────────────────────────

let state = {
  qIdx:            0,
  seconds:         0,
  timer:           null,
  active:          false,
  totalWrongCount: 0,
  difficulty:      'normal',
  questions:       QUESTIONS_NORMAL,
};

// ─── DOM ──────────────────────────────────────────────────────────────────────

const $start    = document.getElementById('start-screen');
const $game     = document.getElementById('game-screen');
const $result   = document.getElementById('result-screen');
const $dialog   = document.getElementById('dialog-overlay');
const $timer    = document.getElementById('timer-value');
const $progFill = document.getElementById('progress-fill');
const $progLbl  = document.getElementById('progress-label');
const $badge    = document.getElementById('q-stage-badge');
const $context  = document.getElementById('scene-context');
const $itemList = document.getElementById('items-list');
const $paidRow  = document.getElementById('paid-row');
const $paidAmt  = document.getElementById('paid-amount');
const $qText    = document.getElementById('q-text');
const $answerRow= document.getElementById('answer-row');
const $feedback = document.getElementById('feedback-msg');
const $diffBadge= document.getElementById('diff-badge');
const $dbEmoji  = document.getElementById('dialog-emoji');
const $dbTitle  = document.getElementById('dialog-title');
const $dbMsg    = document.getElementById('dialog-msg');
const $dbBtns   = document.getElementById('dialog-btns');

// ─── Helpers ──────────────────────────────────────────────────────────────────

function shuffle(arr) {
  const a = arr.slice();
  for (let i = a.length - 1; i > 0; i--) {
    const j = Math.floor(Math.random() * (i + 1));
    [a[i], a[j]] = [a[j], a[i]];
  }
  return a;
}

// ─── Start ────────────────────────────────────────────────────────────────────

function startGame(diff) {
  if (diff !== undefined) {
    state.difficulty = diff;
  }
  // Draw 5 random questions from the difficulty's pool each time, so
  // repeat plays don't always show the same fixed set in the same order.
  state.questions = shuffle(DIFFICULTY[state.difficulty].questions).slice(0, 5);
  state.qIdx            = 0;
  state.seconds         = 0;
  state.active          = true;
  state.totalWrongCount = 0;
  clearInterval(state.timer);
  state.timer = setInterval(tick, 1000);

  const diffCfg = DIFFICULTY[state.difficulty];
  $diffBadge.textContent = diffCfg.label;
  $diffBadge.className   = 'diff-badge ' + diffCfg.cssClass;

  $start.classList.add('hidden');
  $result.classList.add('hidden');
  $game.classList.remove('hidden');
  $dialog.classList.add('hidden');
  document.querySelector('.game-page').classList.add('in-game');

  loadQuestion(0);
}

function loadQuestion(idx) {
  const q = state.questions[idx];

  $badge.textContent   = q.stageLabel;
  $context.textContent = q.context;
  $qText.textContent   = q.qText;
  $feedback.className  = 'feedback-msg hidden';

  // Two option shapes: plain-text choices (`q.options`, e.g. store names or
  // discount plans) for scenario/comparison questions, or the legacy
  // numeric answer/wrong pair (rendered with a unit suffix, "元" by default
  // but overridable via `answerUnit` for things like leg counts).
  const rawOptions = q.options
    ? q.options.map(o => ({ label: o.label, correct: !!o.correct }))
    : [
        { label: `${q.answer} ${q.answerUnit || '元'}`, correct: true },
        { label: `${q.wrong} ${q.answerUnit || '元'}`,  correct: false },
      ];
  const options = shuffle(rawOptions);

  $answerRow.innerHTML = '';
  options.forEach(opt => {
    const btn = document.createElement('button');
    btn.className        = 'option-btn';
    btn.textContent       = opt.label;
    btn.dataset.correct   = opt.correct;
    btn.addEventListener('click', () => onOptionSelect(btn));
    $answerRow.appendChild(btn);
  });

  $itemList.innerHTML = '';
  q.items.forEach(item => {
    const chip = document.createElement('div');
    chip.className = 'item-chip';
    chip.innerHTML = `
      <span class="item-emoji">${item.emoji}</span>
      <span class="item-name">${item.name}</span>
      <span class="item-price">${item.price} ${item.priceUnit || '元'}</span>
      ${item.qty ? `<span class="item-qty">× ${item.qty} ${item.unit || '顆'}</span>` : ''}
    `;
    $itemList.appendChild(chip);
  });

  if (q.paid) {
    $paidRow.style.display = 'flex';
    $paidAmt.textContent   = `${q.paid} 元`;
  } else {
    $paidRow.style.display = 'none';
  }

  const total = state.questions.length;
  $progFill.style.width = `${(idx / total) * 100}%`;
  $progLbl.textContent  = `第 ${idx + 1} 題 / 共 ${total} 題`;
}

// ─── Submit ───────────────────────────────────────────────────────────────────

function onOptionSelect(btnEl) {
  if (btnEl.disabled) return;
  const isCorrect = btnEl.dataset.correct === 'true';

  if (isCorrect) {
    btnEl.className     = 'option-btn correct';
    Array.from($answerRow.children).forEach(b => b.disabled = true);
    $feedback.className = 'feedback-msg correct';
    $feedback.innerHTML = '🎉 答對了！非常好！';

    setTimeout(() => {
      state.qIdx++;
      if (state.qIdx >= state.questions.length) {
        onAllDone();
      } else {
        loadQuestion(state.qIdx);
      }
    }, 1200);
  } else {
    state.totalWrongCount++;
    btnEl.className     = 'option-btn wrong';
    btnEl.disabled       = true;
    $feedback.className = 'feedback-msg wrong';
    $feedback.innerHTML = '❌ 不對喔，再算算看！';
  }
}

// ─── Timer ────────────────────────────────────────────────────────────────────

function tick() {
  state.seconds++;
  const m = Math.floor(state.seconds / 60);
  const s = state.seconds % 60;
  $timer.textContent = `${m}:${s.toString().padStart(2, '0')}`;
}

// ─── Completion ───────────────────────────────────────────────────────────────

function onAllDone() {
  clearInterval(state.timer);
  state.active = false;
  $progFill.style.width = '100%';
  $progLbl.textContent  = '全部完成！';
  showResult();
}

// ─── Score ────────────────────────────────────────────────────────────────────

function calcScore() {
  const diffBonus = { easy: 0, normal: 100, hard: 200 };
  const totalQ    = state.questions.length;

  const rawCompletion = Math.round((state.qIdx / totalQ) * 500);
  const penalty       = Math.min(rawCompletion, state.totalWrongCount * 20);
  const completionPts = rawCompletion - penalty;
  const speedPts      = Math.max(0, Math.round(300 * (1 - state.seconds / 180)));
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

function showResult() {
  const score = calcScore();

  document.getElementById('result-outcome').textContent = '🏆 全部答對！';

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
