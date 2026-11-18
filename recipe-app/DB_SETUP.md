# 資料庫建置

## 步驟 1：還原備份 `sport_game_1.0.dump`

備份（2026-11-18 匯出，PostgreSQL 17）已經包含所有資料表和資料，
**下面 15 支 SQL 的內容也都已經在裡面了**（含 `schema_assistant_profile_gaps.sql`）。
> 🔒 **備份檔不要放上 GitHub**：裡面有使用者帳號、密碼雜湊、健康狀況。
> 用雲端硬碟私人連結、LINE 檔案或 USB 傳給組員；傳到 server 用 `scp`（見 1-B）。
> `.gitignore` 已排除 `*.dump`。

### 1-A　本機（Windows）

Windows 安裝 PostgreSQL 後，`psql`、`pg_restore` 通常**不在 PATH 裡**，要用完整路徑
（`17` 換成你安裝的版本）。以下在 PowerShell 執行：

```powershell
$PG = "C:\Program Files\PostgreSQL\17\bin"

# 1. 建立空的資料庫（已經有 sport_game 就跳過）
& "$PG\createdb.exe" -U postgres sport_game

# 2. 還原備份（路徑換成你放備份的位置）
& "$PG\pg_restore.exe" -U postgres -d sport_game --no-owner "C:\Users\你的名字\Desktop\sport_game_1.0.dump"

# 3. 確認：應該看到 is_on_medication、diet_type 兩列
& "$PG\psql.exe" -U postgres -d sport_game -c "SELECT column_name FROM information_schema.columns WHERE table_name='user_profiles' AND column_name IN ('is_on_medication','diet_type');"
```

每個指令都會問 postgres 的密碼。
不想打完整路徑的話，可以把 `C:\Program Files\PostgreSQL\17\bin` 加到系統環境變數 Path，重開終端機後就能直接打 `psql`。

**已經有舊的 `sport_game`、想整個換成備份**（舊資料會全部刪掉，先確認不需要了）：

```powershell
& "$PG\dropdb.exe" -U postgres sport_game
& "$PG\createdb.exe" -U postgres sport_game
& "$PG\pg_restore.exe" -U postgres -d sport_game --no-owner "C:\...\sport_game_1.0.dump"
```

### 1-B　Server（Linux）

**① 在本機把備份傳上去**（PowerShell，Windows 10 以上內建 `scp`）：

```powershell
scp "C:\Users\你的名字\Desktop\sport_game_1.0.dump" 帳號@server的IP:/tmp/
```

**② 連上 server 還原：**

```bash
ssh 帳號@server的IP

# server 的 PostgreSQL 版本要 ≥ 17（備份是 17.6 匯出的，舊版還原不了）
psql --version

sudo -u postgres createdb sport_game
sudo -u postgres pg_restore -d sport_game --no-owner /tmp/sport_game_1.0.dump

# 確認
sudo -u postgres psql -d sport_game -c "SELECT count(*) FROM users;"

# 還原完刪掉暫存的備份
rm /tmp/sport_game_1.0.dump
```

**③ 拉程式碼、裝套件、設定 `.env`：**

```bash
git clone https://github.com/Julie08080808/sport_game.git   # 第一次
cd sport_game && git pull                                     # 之後更新
cd recipe-app
pip install -r requirements.txt
```

`.env` 裡的資料庫連線要指到 server 的 `sport_game`；`WORKER_APP_SECRET` 等金鑰也要補上
（`.env` 一樣不放 GitHub，私下傳）。

還原完就可以用了，不用再跑下面的 SQL。

## 步驟 2：之後新增的 SQL

在 `sport_game_1.0.dump` **之後**才加的 SQL，要在還原後依序補跑：

```bash
psql -U postgres -d sport_game -f <檔名>
```

（目前沒有。新增時列在這裡。）

## 參考：各 SQL 的用途與順序

已經包含在 `sport_game_1.0.dump` 裡。只有在不用備份、要從頭建時才需要照這個順序跑，
而且 `user_profiles`、`health_conditions`、`recipes`、`ingredients`、`exercise_definitions`
等表沒有對應的建表 SQL，只存在備份裡。

## 1. 建立基本資料表

| # | 檔案 | 內容 |
|---|------|------|
| 1 | `schema_users.sql` | 帳號、遊戲數值、場景、運動紀錄（`users` 等，其他表都會參照它） |
| 2 | `schema_npc.sql` | NPC 對話、任務歷史 |
| 3 | `schema_quiz.sql` | 益智問答題庫 |
| 4 | `schema_shop.sql` | 商店商品、使用者道具 |
| 5 | `schema_tasks.sql` | 新版任務系統（`tasks`、`npcs`、任務進度…） |
| 6 | `schema_profile.sql` | 個人檔案：服裝、成就、設定、飲食回顧 |
| 7 | `schema_assistant_sessions.sql` | 登入 session token（阿明 `/api/assistant/chat` 用） |

## 2. 補欄位／修正

| # | 檔案 | 內容 |
|---|------|------|
| 8 | `schema_tasks_abandon_reason.sql` | `user_task_progress` 補 `abandon_reason` |
| 9 | `schema_tasks_bonus_target_count.sql` | `tasks` 補 `bonus_target_count`（限時超標加成） |
| 10 | `schema_task_is_listed_fix.sql` | 修正咪兔「抬手挑戰」不會發放 |
| 11 | `schema_assistant_profile_gaps.sql` | 阿明資料缺口：服藥、素食欄位，過敏原詞彙，補 `condition_id` |

## 3. 任務與運動資料

| # | 檔案 | 內容 |
|---|------|------|
| 12 | `schema_ball_press_tasks.sql` | 姜泰喵雙球任務＋台詞 |
| 13 | `schema_timed_tasks.sql` | 新增 8 個計次／計時 NPC 任務 |
| 14 | `schema_monkey_kick_tasks.sql` | 山林猴踢腿任務 |
| 15 | `schema_self_training_goal_options.sql` | 自主運動的時間／次數選項 |

## 新增 SQL 時

1. 檔名用 `schema_<功能>.sql`，開頭註解寫日期和用途。
2. 盡量寫成可重複執行（`IF NOT EXISTS`、`ON CONFLICT DO NOTHING`）。
3. **把它加到「步驟 2」**，並提醒組員和 server 都要執行一次。
4. 重新匯出備份時（`pg_dump -U postgres -Fc sport_game -f sport_game_X.Y.dump`），
   把步驟 2 的檔案移到參考清單、步驟 1 的檔名改成新備份。
