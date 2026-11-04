# 專案交接文件（2026-11-04）

此文件整理「運動遊戲」專案（後端 `recipe-app` + Unity 前端）目前的進度，供團隊交接、後續接手參考。

- 後端：`C:\Users\user\Desktop\專題\sport_game\recipe-app`（Git 已連 GitHub：`https://github.com/Julie08080808/sport_game.git`，目前在分支 `feature/shop-quiz-tasks`）
- 前端：Unity 專案 `D:\lastdance\IM_Project\sport_game\sport_game\`（今天剛設定本機 Git，尚未連 GitHub 遠端）

---

## 一、已完成功能

### 1. 任務系統核心修正
- **任務卡死 bug**：超過 24 小時未完成的任務會同時卡住 NPC 新任務發放與資料夾顯示，已修正。
- **閒置自動放棄**：任務進行中超過 1 小時沒有新進度，系統會自動標記為「放棄」，NPC 恢復可發新任務（`expire_stale_progress`）。
- **劇情任務改為冷卻制**：原本完成一次就永久不能再接，改成「領獎後 1 小時冷卻」，冷卻完可以再次挑戰。
- **NPC 任務優先度平衡**：修正多個 NPC 因任務 `priority` 設定不一致，導致某些任務永遠不會被抽到的問題。

### 2. 「我的任務」資料夾 → 改為歷史紀錄
- **後端**：
  - `GET /api/tasks/folder?date=yyyy-MM-dd`：查某一天的完成/放棄紀錄，不帶 `date` 預設查今天；待領獎任務不受日期篩選，永遠顯示。
  - `GET /api/tasks/folder/calendar?year=&month=`：回傳該月有紀錄的日期清單，給月曆畫標記點用。
  - 紀錄**永久保留**，不再是「隔天消失」。
- **Unity**：
  - 新增 `CalendarDayCell.cs`、`CalendarGridController.cs`：月曆格子元件（6 週×7 天、上月/下月切換、標記點、選取外框）。
  - `TaskFolderPanelController.cs`：接上月曆，點日期文字（例如「2026.11.3」）會彈出月曆覆蓋畫面，選完日期自動收起、清單重新整理。
  - `TaskFolderItemView.cs`：每筆紀錄顯示日期、任務名稱、狀態（已完成／任務失敗／已放棄）。
  - **Unity 編輯器端進度**：
    - ✅ Phase 1（`DayCell` Prefab）：完成，欄位接好。
    - ✅ Phase 2（月曆整體版面：月份標題、上下月按鈕、`CellContainer` + `CalendarGridController` 接線）：完成。
    - 🟡 Phase 3（`TaskFolderPanelController` 的 4 個新欄位 `calendarOverlayRoot`／`calendar`／`selectedDateLabelText`／`selectedDateButton` 接線）：`SelectedDateButton` 物件已建立在正確位置（`FolderPanel` 底下），**但 4 個欄位是否已經拖好尚未截圖確認**。
    - ⬜ Phase 4（實機測試：打開資料夾 → 點日期 → 月曆彈出 → 選日期 → 清單正確更新）：**尚未開始**。

### 3. 限時挑戰（計時任務）機制
- 60 秒倒數、達標過關、超標雙倍經驗的「限時挑戰」機制，從原本只有「抬手挑戰」擴充到全部 6 種運動都有對應的計時任務版本。
- **Bug 修正**：
  - 進度條/次數文字在超過合格門檻時顯示異常（例如「25/20」）：已修正（`ExerciseSessionController.RefreshProgressUI`）。
  - `ExerciseLegScene` 缺少倒數計時、挑戰失敗面板 UI：已透過手動複製 GameObject 從 `ExerciseHandScene` 補齊，並重新接線完成。
- **設計變更**：限時挑戰失敗後**不能再「重新挑戰」**，只能返回地圖，並在資料夾顯示為「任務失敗」（跟一般「放棄」分開標示）。
  - 後端：新增 `abandon_reason` 欄位（`manual` / `challenge_timeout`），`/api/tasks/abandon` 可帶 `reason`。
  - Unity：`ExerciseRepFlowController.cs` 整個移除「重新挑戰」相關程式碼（`retryChallengeButton`、`OnRetryChallengeClick`、`RetryChallengeRoutine`）；`ExerciseHandScene`、`ExerciseLegScene` 的 `RetryChallengeButton` 物件已刪除。

### 4. 六種運動完整補齊
- 新增動作定義與辨識服務，讓以下 6 種運動都能實際遊玩：
  - 猴子（山林猴）：踏步 `STEP`、踢腳 `KICK`
  - 兔子（咪兔）：抬手 `ARM_RAISE`（原有）、二頭彎舉 `BICEP_CURL`
  - 石虎（姜太喵）：手按球 `HAND_PRESS`、腳按球 `FOOT_PRESS`
- 新增 4 支辨識服務腳本：`KickRecognitionService.cs`、`BicepCurlRecognitionService.cs`、`HandPressRecognitionService.cs`、`FootPressRecognitionService.cs`。
- `ExerciseCountTaskRules.cs` 白名單同步擴充。
- 後端新增對應 `exercise_definitions`、11 個新任務（6 個計次＋5 個限時挑戰）、共 88 筆對話文字（`task_story_steps`）。
- **示範圖片系統**：`ExercisePreparationController.cs` 改成依 `exerciseKey` 查表取圖（`List<ExerciseSpriteEntry>`），之後新增運動不用改程式碼，Inspector 加一筆對應圖即可。目前**暫用現有圖片代替**，六種運動各自的正式示範圖還沒畫。
- **運動中動畫圖（`ExerciseContentSequencePlayer`）**：同樣改成依 `recognitionKey` 查表切換 idle/動作/完成圖，讓同一場景（例如 `ExerciseLegScene` 同時給 STEP、KICK 用）可以各自顯示自己的動畫圖，**Inspector 的 `Exercise Frame Sets` 清單還沒實際填圖**。

### 5. MainMap1 / MainMap2 場景切換
- 刪除舊的單向暫時腳本 `TempGoToMainmap2.cs`，換成正式的雙向 `SceneSwitchButton.cs`（掛在按鈕上，`Target Scene Name` 填目標場景名稱即可重複使用）。
- **狀態不確定**：已給出操作步驟（MainMap1 按鈕換新腳本、Mainmap2 新增返回按鈕），但**還沒收到截圖確認完成**，中途被 WebCam package 的緊急狀況打斷。

### 6. Unity 專案版本控制與備份
- **根因排除**：確認專案完全沒有 Git／Plastic SCM 保護，匯入隊友的 `.unitypackage` 曾經因為 GUID 覆蓋問題，搞壞 3 個 Prefab（`ExperienceManager`、`Building_Farm`、`Canvas`）跟整個限時挑戰功能，當時靠對話記憶手動重寫救回來。
- 今天已經：
  - 建立完整備份：`D:\lastdance\IM_Project\sport_game\sport_game_backup_20261104\`
  - 初始化本機 Git（含 Unity 專用 `.gitignore`，排除 `Library`/`Temp` 等可重建的快取），已有第一個還原點（commit `cbcb4e9`）。
  - **尚未連接 GitHub 遠端**：已決定前端用獨立的新 repo（跟後端的 `Julie08080808/sport_game` 分開），但 repo 還沒建立，在等你提供 GitHub 網址。

### 7. 隊友電腦無法開啟專案（已解決）
- 根因：`Packages/manifest.json` 裡有一個套件（藍芽函式庫 `com.velorexe.androidbluetoothlowenergy`）是直接從 GitHub 抓原始碼，隊友電腦解析失敗，連帶拖垮整個套件清單，導致幾乎所有腳本都報 `CS0246`/`CS0234` 編譯錯誤（找不到 `TMPro`、`UnityEngine.UI`、`InputSystem` 等命名空間）。
- 解法：把本機已經解析好的套件快取（`Library/PackageCache/com.velorexe.androidbluetoothlowenergy@1b7dc9548bb3`，64KB）直接打包傳給隊友，放進她專案對應路徑，不需要她的電腦重新連線解析。
- **結果：隊友電腦已經可以正常開啟專案了。**

---

## 二、討論過、但尚未動工的功能

以下是這次討論過設計方向、但程式碼完全還沒開始寫的項目：

- **自主運動（自由訓練）**：目前完全沒有對應的畫面與邏輯，是全新功能。
- **商店功能**：畫面與邏輯都還沒做。
- **預錄音檔作暖身語音指導**：新提出的功能構想，還沒規劃細節。
- **示範影片（取代示範圖片）**：原始構想是依 NPC 對話文字挑對應的示範影片，後來先改成「依運動種類換圖片」這個比較小的版本（已完成架構，見上方第 4 點），真正的「影片」版本還沒做。

---

## 三、尚未解決／待確認的事項

1. **後端 Git 有未提交的變更**：今天新增的 `abandon_reason` 欄位、`AbandonRequest`、`/api/tasks/folder` 的 `date` 參數、`/api/tasks/folder/calendar` 端點，都還**沒有 commit 到後端 Git**（`recipe-app`）。另外，先前 commit `bd8c125`之後也還有一版資料夾查詢條件的修改沒進版控。建議近期找時間一起過一遍、整理後 commit。
2. **資料夾月曆 Phase 3～4**：欄位接線跟實機測試都還沒做完（詳見上方第 2 點）。
3. **MainMap1↔2 切換按鈕**：還沒收到完成截圖確認。
4. **WebCam1104 package**：目前還**沒有匯入**（當初取消了，先去處理隊友的編譯錯誤問題），如果還需要這個功能要再找時間處理，記得匯入前先跟現有檔案比對 GUID 衝突。
5. **Unity 前端 GitHub repo**：還沒建立，等你提供網址後我會幫你把今天的進度推上去，並寫一份簡單的 push/pull 操作說明。
6. **六種運動的正式示範圖片／動畫圖**：目前都是暫用舊圖，欄位架構做完了，缺美術素材。

---

## 四、完整待辦清單（原始需求，依狀態分類）

### A：介面問題
- [ ] 設定按鈕：音效/語音開關測試、UI 風格更換
- [ ] 全部文字放大
- [🟡] 資料夾改「歷史紀錄」＋月曆（進度見上方，Phase 3～4 未完）
- [ ] NPC 對話框風格統一
- [ ] 運動各種畫面（美術）
- [ ] 自主運動畫面
- [ ] 商店畫面

### B：流程問題
- [🟡] 暖身運動依手/腳/球（已做完欄位架構，缺實際圖片）
- [✅] 計時功能 bug（進度條/文字/倒數 UI 全部修好）
- [ ] 任務場景切換：每個 NPC 都要能切場景；景點場景升級後的畫面
- [ ] 藍芽雙球功能
- [ ] 自主運動：缺畫面、缺邏輯（全新功能）
- [ ] 商店功能未完成

### C：串接
- [ ] 老鼠 NPC：食譜功能、問答遊戲串接
- [ ] 躺著的熊：益智遊戲串接
- [ ] 拍照功能串接
- [ ] AI 串接

### D：部署
- [ ] 掛上正式 server

### 新增功能
- [ ] 預錄音檔作為運動暖身指導

---

## 五、資料庫同步（重要，隊友 pull 下來後要做）

專案沒有用 migration 工具，資料庫欄位異動都是直接下 SQL 改的，不會自動同步。每個人本機 Postgres（預設 `localhost`）都要自己手動補上以下異動，不然 API 會噴 SQL 錯誤：

```sql
ALTER TABLE user_task_progress ADD COLUMN IF NOT EXISTS abandon_reason VARCHAR(20) NOT NULL DEFAULT 'manual';
```

（其餘今天異動的 `exercise_definitions`、`tasks`、`npc_task_assignments`、`task_story_steps` 相關 INSERT/UPDATE，屬於資料內容而非欄位結構，若隊友的資料庫跟你是各自獨立的測試資料，不用特別同步；若你們共用同一顆資料庫就不用管這段。）

## 六、給接手者的技術備註

- **後端**：FastAPI + PostgreSQL，資料庫時區為 `Asia/Taipei`，`CURRENT_TIMESTAMP`/`CURRENT_DATE` 已經是台灣當地時間。
- **Unity**：目前走「計次動作」白名單架構（`ExerciseCountTaskRules.cs`），新增運動動作要同步修改白名單 + 寫對應的 `XxxRecognitionService.cs`。
- **場景路由**：`exercise_scene_key` 為 `hand`/`ball` 都會進 `ExerciseHandScene`，`leg` 進 `ExerciseLegScene`；`ExerciseBallScene.unity` 目前是沒人用的孤兒場景，不用維護。
- **版控**：
  - 後端：Git + GitHub（`Julie08080808/sport_game`），多人協作中。
  - 前端：Git（本機已設定），GitHub 遠端待建立。
  - Unity 專案開啟前**務必確認沒有同時被兩人修改同一個場景**，目前沒有用 Unity VCS 的語意合併，場景衝突要自己留意。
