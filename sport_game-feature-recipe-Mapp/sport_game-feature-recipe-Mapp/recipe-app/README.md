# 銀髮族食譜 App

針對銀髮族設計的食譜瀏覽網頁,採用大字體、卡片式介面以及左右滑動瀏覽。

## 開發環境與架構

| 類別 | 技術 |
|------|------|
| 語言 | Python 3.x |
| Web 框架 | FastAPI |
| 資料庫 | PostgreSQL |
| 驗證 | 簡易帳密比對(不需 JWT、不需 Email) |
| 上傳檔案 | FastAPI 的 `UploadFile` |
| 前端介面 | HTML / CSS / JavaScript |
| 測試執行 | `uvicorn main:app --reload` |

## MVC 架構說明

```
recipe-app/
├── main.py                      # 應用程式進入點
├── .env                         # 資料庫密碼(不上傳 GitHub)
├── .env.example                 # 環境變數範本(可上傳)
├── .gitignore                   # Git 忽略清單
├── requirements.txt             # Python 套件
├── schema_users.sql             # users 資料表建立腳本
│
├── config/                      # 設定層
│   └── database.py              #   資料庫連線(讀 .env)
│
├── models/                      # M - Model 資料模型層
│   ├── recipe_model.py          #   食譜資料存取
│   └── user_model.py            #   使用者資料存取
│
├── controllers/                 # C - Controller 控制器層
│   ├── recipe_controller.py     #   食譜 API
│   ├── user_controller.py       #   登入/註冊 API
│   └── upload_controller.py     #   圖片上傳 API
│
├── views/                       # V - View 視圖層
│   ├── index.html               #   食譜首頁
│   ├── login.html               #   登入/註冊頁
│   ├── style.css
│   ├── script.js
│   └── login.js
│
├── image/                       # 食譜圖片(原本就有)
└── 食譜/                         # 食譜素材(原本就有)
```

## 安裝與啟動

### 1. 安裝套件

```bash
pip install -r requirements.txt
```

### 2. 設定 `.env`

複製 `.env.example` 為 `.env`,填入您的資料庫資訊:

```
DB_NAME=test_rec_0404
DB_USER=postgres
DB_PASSWORD=您的密碼
DB_HOST=localhost
DB_PORT=5432
```

### 3. 建立 users 資料表(支援登入功能)

```bash
psql -U postgres -d test_rec_0404 -f schema_users.sql
```

### 4. 啟動伺服器

```bash
uvicorn main:app --reload
```

### 5. 開啟瀏覽器

- 首頁:http://localhost:8000
- 登入:http://localhost:8000/login
- API 文件:http://localhost:8000/docs

## API 列表

| 方法 | 路徑 | 說明 |
|------|------|------|
| GET  | `/api/recipes` | 取得所有食譜 |
| GET  | `/api/recipes/{id}/steps` | 取得指定食譜步驟 |
| POST | `/api/users/register` | 註冊 |
| POST | `/api/users/login` | 登入 |
| POST | `/api/upload/image` | 上傳圖片 |

## 資安注意事項(GitHub 上傳前必看)

1. **絕對不要上傳 `.env`** — 已在 `.gitignore` 中忽略,推送前請執行:
   ```bash
   git status
   ```
   確認列表中**沒有** `.env`。

2. **若不小心已 commit `.env`**,請更換密碼並執行:
   ```bash
   git rm --cached .env
   git commit -m "Remove .env from tracking"
   ```

3. **預設測試帳號**(`admin` / `1234`)正式上線前請刪除。

4. **目前密碼為明文儲存**,正式環境建議改用 `bcrypt` 雜湊。
