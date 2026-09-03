-- 商店系統資料表
-- 在 PostgreSQL 中執行:
--   psql -U postgres -d sport_game -f schema_shop.sql

-- 商店商品清單
CREATE TABLE IF NOT EXISTS shop_items (
    item_id SERIAL PRIMARY KEY,
    item_name VARCHAR(50) NOT NULL,
    description VARCHAR(200),
    price INTEGER NOT NULL DEFAULT 0,
    icon_url VARCHAR(200),
    category VARCHAR(30) NOT NULL DEFAULT 'general',
    is_active BOOLEAN NOT NULL DEFAULT TRUE
);

-- 玩家已購買的商品(背包/庫存)
CREATE TABLE IF NOT EXISTS user_items (
    user_id INTEGER NOT NULL REFERENCES users(user_id),
    item_id INTEGER NOT NULL REFERENCES shop_items(item_id),
    quantity INTEGER NOT NULL DEFAULT 0,
    PRIMARY KEY (user_id, item_id)
);

-- 預設上架一些對齊現有場景主題(農場/池塘/森林/中心/果園)的商品,方便展示
INSERT INTO shop_items (item_name, description, price, icon_url, category) VALUES
    ('小狗裝飾', '放在農場旁的可愛小狗擺飾', 50, '/image/ui/animal-dog.png', 'decoration'),
    ('小貓裝飾', '放在森林旁的可愛小貓擺飾', 50, '/image/ui/animal-cat.png', 'decoration'),
    ('狐狸裝飾', '放在森林旁的狐狸擺飾', 80, '/image/ui/animal-fox.png', 'decoration'),
    ('兔子裝飾', '放在農場旁的兔子擺飾', 80, '/image/ui/animal-rabbit.png', 'decoration'),
    ('猴子裝飾', '放在果園旁的猴子擺飾', 100, '/image/ui/animal-monkey.png', 'decoration'),
    ('魚桶', '池塘釣魚道具,可加快池塘經驗累積', 150, '/image/ui/fish-bucket.png', 'booster')
ON CONFLICT DO NOTHING;
