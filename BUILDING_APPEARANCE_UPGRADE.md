# 建築外觀升級功能 — 給 Claude 的實作指南

> 這份文件是寫給另一個 Claude Code 讀的，目的是在**同伴的電腦上重現一模一樣的功能**。
> 如果你是 Claude，請照這份文件的順序執行；遇到「⚠️ 給人類做」的步驟，主動引導使用者在 Unity Editor 裡操作，
> 不要自己手動改 `.unity` 場景檔案的 UI 階層（Canvas/Panel/Button 這種），理由見文末「踩過的坑」。

## 功能總覽

玩家在某個場景（農場/池塘/森林/中心/商店）完成任務，該場景的「完成次數」+1；每滿 **20 次**，場景等級 +1，
建築外觀自動換成新解鎖的階段圖片。玩家也可以手動把某一棟建築的外觀**調回之前已解鎖過的舊階段**，
每棟建築的選擇彼此獨立，不會互相影響；場景再升級時，該棟建築的手動覆寫會被清空、變回顯示最新階段。

資料庫負責「這個帳號在這個場景解鎖到第幾階、目前手動選第幾階」這兩個數字；Unity 端的 `BuildingData.stages`
陣列負責「每一階要顯示哪張圖」——資料庫完全不知道圖片的事，只回傳數字。

---

## Part 1：後端（已經在 git 裡，直接 pull 就好）

後端改動已經 commit 並 push 到 GitHub `sport_game` repo 的 `feature/shop-quiz-tasks` 分支
（commit `03836f6`）。**這部分不用重寫，執行：**

```bash
git fetch origin
git checkout feature/shop-quiz-tasks   # 或直接 merge/pull 這個分支到你在用的分支
```

拿到程式碼後，套用資料庫 schema（`IF NOT EXISTS` 寫法，跑在已有資料的資料庫上也安全，不會刪資料）：

```bash
cd recipe-app
psql -U postgres -d sport_game -f schema_tasks.sql
```

### API 合約參考（給你確認 Unity 端串接對不對用）

| 端點 | 用途 |
|---|---|
| `POST /api/npc/task/complete`（`user_id`, `task_progress_id`） | 完成任務，發獎勵，場景完成次數 +1，滿 20 次升級並清空該場景的手動外觀覆寫。回傳含 `leveled_up`(bool)、`scene_level`、`completion_count`、`display_level_cap` |
| `GET /api/game/scenes/{user_id}` | 取得該玩家目前**所有**場景的 `scene_id`/`scene_level`/`scene_exp`/`completion_count`/`display_level_cap`。會自動幫玩家補齊「新加的場景但這個帳號還沒有紀錄」的資料，舊帳號不用手動遷移 |
| `POST /api/game/scene/display_level`（`user_id`, `scene_id`, `display_level`） | 玩家手動指定某場景要顯示第幾階外觀；`display_level` 傳 `-1` 代表清除覆寫、改回自動顯示最新解鎖階段；傳的值必須 `0 ~ scene_level` 之間，否則回 400 |

**重要**：`display_level_cap` 這個欄位資料庫存的是 `NULL`（代表沒覆寫），但 API 對外一律把 `NULL` 轉成 `-1`
才回傳——因為 Unity 的 `JsonUtility` 沒辦法把 JSON `null` 安全讀進 C# 的 `int` 欄位。Unity 端所有相關欄位一律用
`int`、`-1` 當作「沒有覆寫」的語意，不要用 nullable int。

---

## Part 2：Unity 新增檔案（完整原始碼，直接建立這些檔案）

以下 4 個是全新檔案，Unity 專案裡本來不存在，直接照內容建立即可，不會跟同伴既有的東西衝突。
每個 `.cs` 檔案都要有對應的 `.meta`——**建立 `.cs` 檔案後讓 Unity 自動產生 `.meta`**（開啟 Unity Editor、
等它偵測到新檔案自動 import 即可，不用自己寫 `.meta` 內容，Unity 會自動生成正確的 GUID）。

### `Assets/scripts/BuildingStageOptionButton.cs`

```csharp
using System;
using UnityEngine;
using UnityEngine.UI;
using TMPro;

// 掛在「建築外觀選擇視窗」裡單一選項按鈕的 Prefab 上，由 BuildingStagePickerPanel 動態 Instantiate。
public class BuildingStageOptionButton : MonoBehaviour
{
    public Image iconImage;
    public TextMeshProUGUI labelText;
    public Button button;

    public void Setup(Sprite icon, string label, Action onClick)
    {
        if (iconImage != null) iconImage.sprite = icon;
        if (labelText != null) labelText.text = label;

        if (button != null)
        {
            button.onClick.RemoveAllListeners();
            button.onClick.AddListener(() => onClick?.Invoke());
        }
    }
}
```

### `Assets/scripts/BuildingStagePickerPanel.cs`

```csharp
using System.Collections.Generic;
using UnityEngine;
using TMPro;

// 建築外觀選擇的懸浮視窗：點建築時開啟，只列出「目前已解鎖」的階段讓玩家選擇要顯示哪一個，
// 不列未解鎖的(選了也沒用，直接不給選)。選完呼叫後端 /api/game/scene/display_level，
// 每棟建築各自獨立，互不影響——這棟選舊外觀，不會連動到其他棟。
// 掛在這個選擇視窗的根物件上。
public class BuildingStagePickerPanel : MonoBehaviour
{
    public static BuildingStagePickerPanel Instance;

    [Header("UI 元件")]
    public GameObject panelRoot;
    [Tooltip("階段選項按鈕要生成到哪個容器下")]
    public Transform contentParent;
    [Tooltip("單一階段選項的按鈕 Prefab")]
    public BuildingStageOptionButton optionButtonPrefab;
    public TextMeshProUGUI titleText;

    private readonly List<BuildingStageOptionButton> spawnedOptions = new List<BuildingStageOptionButton>();
    private BuildingManager targetManager;

    private void Awake()
    {
        if (Instance == null) Instance = this;
        if (panelRoot != null) panelRoot.SetActive(false);
    }

    // 由 BuildingManager.OpenStagePicker() 呼叫
    public void Show(BuildingManager manager)
    {
        if (manager == null || manager.data == null || manager.data.stages == null)
            return;

        targetManager = manager;

        if (titleText != null)
            titleText.text = $"{manager.data.buildingName} 外觀選擇";

        ClearOptions();

        for (int i = 0; i < manager.data.stages.Count; i++)
        {
            BuildingLevelStage stage = manager.data.stages[i];

            // 還沒解鎖的階段不列出來，避免玩家選到選不到的東西
            if (stage.unlockLevel > manager.data.level)
                continue;

            int stageIndex = i;
            BuildingStageOptionButton option = Instantiate(optionButtonPrefab, contentParent);
            option.Setup(stage.visualSprite, $"Lv.{stage.unlockLevel}", () => OnPickStage(stageIndex));
            spawnedOptions.Add(option);
        }

        if (panelRoot != null) panelRoot.SetActive(true);
    }

    // 綁在關閉按鈕的 OnClick 上
    public void Hide()
    {
        if (panelRoot != null) panelRoot.SetActive(false);
        targetManager = null;
    }

    private void OnPickStage(int stageIndex)
    {
        if (targetManager == null) return;

        targetManager.SetDisplayStage(stageIndex);
        Hide();
    }

    private void ClearOptions()
    {
        foreach (BuildingStageOptionButton option in spawnedOptions)
        {
            if (option != null) Destroy(option.gameObject);
        }
        spawnedOptions.Clear();
    }
}
```

### `Assets/scripts/EditorAutoLogin.cs`

開發測試用的捷徑，不影響正式版本行為（`#if UNITY_EDITOR` 保護）。用途：直接開 MainMap 按 Play
（不走 LoginScene）時自動登入一組測試帳號，方便測試需要知道玩家身份的功能。

```csharp
using System.Collections;
using UnityEngine;
using UnityEngine.Networking;

// 開發測試用：直接開 MainMap 按 Play(沒有走 LoginScene)時，自動用測試帳號登入，
// 方便測試需要知道玩家身份的功能(換外觀、NPC任務、商店...)。
// 只有在 Unity Editor 裡執行時才會生效，真機/正式建置版本 Start() 會直接空跑，不影響上架版本的行為。
// 用法：在 MainMap 場景裡建一個空物件掛這支腳本即可，不需要接任何欄位。
public class EditorAutoLogin : MonoBehaviour
{
    [Header("測試帳號(僅供 Editor 內測試使用)")]
    [SerializeField] private string testUsername = "editor_test";
    [SerializeField] private string testPassword = "test1234";

    private void Start()
    {
#if UNITY_EDITOR
        if (UserSession.Instance.IsLoggedIn())
            return;

        StartCoroutine(AutoLogin());
#endif
    }

    private IEnumerator AutoLogin()
    {
        WWWForm form = new WWWForm();
        form.AddField("username", testUsername);
        form.AddField("password", testPassword);

        string url = $"{NetworkManager.GetInstance().serverUrl}/api/users/login";

        using (UnityWebRequest req = UnityWebRequest.Post(url, form))
        {
            yield return req.SendWebRequest();

            if (req.result != UnityWebRequest.Result.Success)
            {
                Debug.LogWarning(
                    $"[EditorAutoLogin] 自動登入失敗(連線錯誤): {req.error}\n{req.downloadHandler.text}"
                );
                yield break;
            }

            LoginResponse response = JsonUtility.FromJson<LoginResponse>(req.downloadHandler.text);

            if (response == null || !response.success)
            {
                Debug.LogWarning("[EditorAutoLogin] 自動登入失敗：帳密錯誤或測試帳號不存在");
                yield break;
            }

            UserSession.Instance.Initialize(response.user_id, testUsername);
            Debug.Log($"[EditorAutoLogin] 已自動登入測試帳號，user_id={response.user_id}");

            // ExperienceManager.Start() 可能已經在登入完成前就先跑過(執行順序不保證)，
            // 這裡登入成功後手動再觸發一次場景同步，確保建築外觀還是會正確套用。
            if (ExperienceManager.Instance != null)
            {
                ExperienceManager.Instance.SyncAllScenesFromServer();
            }
        }
    }
}
```

> ⚠️ 這個腳本需要資料庫裡真的有一組 `testUsername`/`testPassword` 帳號才能登入成功。
> 執行 `curl -X POST http://localhost:8000/api/users/register -d "username=editor_test&password=test1234"`
> 註冊一次（或請使用者透過遊戲本身的註冊畫面建立），只要建立一次即可。

### `Assets/Editor/BuildingStagesEditorWindow.cs`

**這個檔案必須放在名字叫 `Editor` 的資料夾底下**（Unity 慣例，這個資料夾的腳本只在編輯器生效，
不會打包進正式版本）。統一管理所有建築外觀階段的工具視窗。

```csharp
using System.Collections.Generic;
using System.Linq;
using UnityEditor;
using UnityEngine;

// 統一管理所有場景建築(Farm/Pond/Forest/Center/Store)的外觀階段。
// 開啟方式：選單列 Game → 建築外觀管理 Building Stages。
// 會自動列出專案裡所有 BuildingData 資產，不用手動註冊，新增場景建築時自動出現。
public class BuildingStagesEditorWindow : EditorWindow
{
    private Vector2 scrollPos;
    private readonly Dictionary<BuildingData, int> previewLevels = new Dictionary<BuildingData, int>();

    [MenuItem("Game/建築外觀管理 Building Stages")]
    public static void Open()
    {
        GetWindow<BuildingStagesEditorWindow>("建築外觀管理");
    }

    private void OnGUI()
    {
        List<BuildingData> all = AssetDatabase.FindAssets("t:BuildingData")
            .Select(guid => AssetDatabase.LoadAssetAtPath<BuildingData>(AssetDatabase.GUIDToAssetPath(guid)))
            .Where(b => b != null)
            .OrderBy(b => b.buildingType)
            .ToList();

        if (all.Count == 0)
        {
            EditorGUILayout.HelpBox(
                "專案裡找不到任何 BuildingData 資產(Assets/Data 底下那些 xxx_Data.asset)。",
                MessageType.Info
            );
            return;
        }

        scrollPos = EditorGUILayout.BeginScrollView(scrollPos);

        foreach (BuildingData building in all)
        {
            DrawBuilding(building);
            EditorGUILayout.Space(12);
        }

        EditorGUILayout.EndScrollView();
    }

    private void DrawBuilding(BuildingData building)
    {
        EditorGUILayout.BeginVertical("box");

        EditorGUILayout.LabelField(
            $"{building.buildingName}（buildingType / scene_id = {building.buildingType}）",
            EditorStyles.boldLabel
        );
        EditorGUILayout.ObjectField("資產檔案", building, typeof(BuildingData), false);

        EditorGUILayout.Space(4);
        EditorGUILayout.LabelField(
            $"目前 level：{building.level}　displayLevelCap：{building.displayLevelCap}"
        );

        EditorGUILayout.Space(4);
        EditorGUILayout.LabelField("外觀階段(Stages)", EditorStyles.boldLabel);

        SerializedObject so = new SerializedObject(building);
        SerializedProperty stagesProp = so.FindProperty("stages");

        for (int i = 0; i < stagesProp.arraySize; i++)
        {
            SerializedProperty stage = stagesProp.GetArrayElementAtIndex(i);
            SerializedProperty unlockLevelProp = stage.FindPropertyRelative("unlockLevel");
            SerializedProperty spriteProp = stage.FindPropertyRelative("visualSprite");

            EditorGUILayout.BeginHorizontal();
            EditorGUILayout.LabelField($"階段 {i}", GUILayout.Width(45));
            EditorGUILayout.PropertyField(unlockLevelProp, new GUIContent("unlockLevel"), GUILayout.Width(150));
            EditorGUILayout.PropertyField(spriteProp, GUIContent.none, GUILayout.Width(160));

            if (GUILayout.Button("刪除", GUILayout.Width(50)))
            {
                stagesProp.DeleteArrayElementAtIndex(i);
            }

            EditorGUILayout.EndHorizontal();
        }

        if (GUILayout.Button("+ 新增階段", GUILayout.Width(100)))
        {
            stagesProp.InsertArrayElementAtIndex(stagesProp.arraySize);
        }

        so.ApplyModifiedProperties();

        EditorGUILayout.Space(6);

        EditorGUILayout.BeginHorizontal();

        if (!previewLevels.ContainsKey(building))
            previewLevels[building] = building.level;

        previewLevels[building] = EditorGUILayout.IntField("預覽等級", previewLevels[building], GUILayout.Width(200));

        if (GUILayout.Button("預覽", GUILayout.Width(80)))
        {
            PreviewBuilding(building, previewLevels[building]);
        }

        EditorGUILayout.EndHorizontal();

        EditorGUILayout.HelpBox(
            "「預覽」只是暫時把 level 設成上面填的數字並刷新畫面，不會存檔、不會連後端。" +
            "要離開預覽的話，重新按 Play 讓它從伺服器同步回真實進度即可。",
            MessageType.None
        );

        EditorGUILayout.EndVertical();
    }

    private void PreviewBuilding(BuildingData building, int previewLevel)
    {
        building.level = previewLevel;
        EditorUtility.SetDirty(building);

        BuildingManager match = Object.FindObjectsByType<BuildingManager>(FindObjectsSortMode.None)
            .FirstOrDefault(m => m.data == building);

        if (match == null)
        {
            Debug.LogWarning(
                $"[建築外觀管理] 目前開啟的場景裡找不到掛著 {building.buildingName} 的 BuildingManager，" +
                "請先打開有這棟建築的場景(例如 MainMap)再預覽。"
            );
            return;
        }

        match.UpdateVisual();
    }
}
```

---

## Part 3：Unity 修改既有檔案

同伴的專案裡這些檔案已經存在（他自己的版本），**不要整檔覆蓋**，只把下面標的內容加進去，
保留他原本已有的其他程式碼。如果某個方法他也改過，先讓使用者確認過內容再動手，不要盲目覆蓋。

### 🟢 低風險：純新增

**`Assets/scripts/BuildingData.cs`** — class 最後面加一個欄位：

```csharp
[Header("玩家手動覆寫的外觀階段 (由後端 user_scenes.display_level_cap 同步)")]
[Tooltip("-1 代表沒有手動覆寫，顯示時直接用 level(最新已解鎖階段)。" +
    "場景升級時後端會自動清空這個值，讓新階段變回預設顯示。")]
public int displayLevelCap = -1;
```

**`Assets/scripts/GameDataSchema.cs`** — 檔案最後面加 4 個類別（檔案最上面要有
`using System.Collections.Generic;`，沒有的話要加）：

```csharp
[Serializable]
public class TaskCompleteResponse
{
    public bool success;
    public string message;
    public int task_id;
    public int task_progress_id;
    public int player_level;
    public int player_exp;
    public int money;
    public int scene_id;
    public int scene_level;
    public int scene_exp;
    public int completion_count;
    public int display_level_cap;
    public bool leveled_up;
}

[Serializable]
public class SceneStatus
{
    public int scene_id;
    public int scene_level;
    public int scene_exp;
    public int completion_count;
    public int display_level_cap;
}

[Serializable]
public class SceneStatusListResponse
{
    public bool success;
    public List<SceneStatus> scenes;
}

[Serializable]
public class SetDisplayLevelResponse
{
    public bool success;
    public string message;
    public int scene_id;
    public int scene_level;
    public int display_level_cap;
}
```

**`Assets/scripts/NetworkManager.cs`** — 在 `GetInstance()` 前面加 3 個方法：

```csharp
public IEnumerator CompleteTask(int uid, int taskProgressId, Action<TaskCompleteResponse> onComplete)
{
    WWWForm form = new WWWForm();
    form.AddField("user_id", uid);
    form.AddField("task_progress_id", taskProgressId);
    string url = $"{serverUrl}/api/npc/task/complete";
    using (UnityWebRequest req = UnityWebRequest.Post(url, form))
    {
        yield return req.SendWebRequest();
        if (req.result != UnityWebRequest.Result.Success)
        {
            Debug.LogError($"[完成任務失敗] HTTP {req.responseCode}, {req.error}\n{req.downloadHandler.text}");
            onComplete?.Invoke(null);
            yield break;
        }
        TaskCompleteResponse response = JsonUtility.FromJson<TaskCompleteResponse>(req.downloadHandler.text);
        onComplete?.Invoke(response);
    }
}

public IEnumerator GetAllSceneStatus(int uid, Action<SceneStatusListResponse> onComplete)
{
    string url = $"{serverUrl}/api/game/scenes/{uid}";
    using (UnityWebRequest req = UnityWebRequest.Get(url))
    {
        yield return req.SendWebRequest();
        if (req.result != UnityWebRequest.Result.Success)
        {
            Debug.LogError($"[取得場景狀態失敗] HTTP {req.responseCode}, {req.error}");
            onComplete?.Invoke(null);
            yield break;
        }
        SceneStatusListResponse response = JsonUtility.FromJson<SceneStatusListResponse>(req.downloadHandler.text);
        onComplete?.Invoke(response);
    }
}

public IEnumerator SetSceneDisplayLevel(int uid, int sceneId, int displayLevel, Action<SetDisplayLevelResponse> onComplete)
{
    WWWForm form = new WWWForm();
    form.AddField("user_id", uid);
    form.AddField("scene_id", sceneId);
    form.AddField("display_level", displayLevel);
    string url = $"{serverUrl}/api/game/scene/display_level";
    using (UnityWebRequest req = UnityWebRequest.Post(url, form))
    {
        yield return req.SendWebRequest();
        if (req.result != UnityWebRequest.Result.Success)
        {
            Debug.LogError($"[設定場景外觀失敗] HTTP {req.responseCode}, {req.error}\n{req.downloadHandler.text}");
            onComplete?.Invoke(null);
            yield break;
        }
        SetDisplayLevelResponse response = JsonUtility.FromJson<SetDisplayLevelResponse>(req.downloadHandler.text);
        onComplete?.Invoke(response);
    }
}
```

**`Assets/scripts/BuildingManager.cs`** — class 最後面加入：

```csharp
[ContextMenu("預覽外觀 Preview Visual")]
private void PreviewVisual()
{
    UpdateVisual();
}

public void OpenStagePicker()
{
    if (BuildingStagePickerPanel.Instance == null)
    {
        Debug.LogWarning("[BuildingManager] 場景裡找不到 BuildingStagePickerPanel，外觀選擇視窗開不起來");
        return;
    }
    BuildingStagePickerPanel.Instance.Show(this);
}

public void SetDisplayStage(int stageIndex)
{
    if (data == null || data.stages == null || stageIndex < 0 || stageIndex >= data.stages.Count)
        return;
    int targetLevel = data.stages[stageIndex].unlockLevel;
    if (targetLevel > data.level)
    {
        Debug.LogWarning($"[BuildingManager] 階段 {stageIndex} 尚未解鎖(需要等級 {targetLevel})，無法選擇");
        return;
    }
    RequestSetDisplayLevel(targetLevel);
}

public void ResetToLatestStage()
{
    RequestSetDisplayLevel(-1);
}

private void RequestSetDisplayLevel(int targetLevel)
{
    if (data == null || UserSession.Instance == null || UserSession.Instance.userId == -1)
        return;
    int uid = UserSession.Instance.userId;
    StartCoroutine(NetworkManager.GetInstance().SetSceneDisplayLevel(uid, data.buildingType, targetLevel, response =>
    {
        if (response == null || !response.success)
        {
            Debug.LogWarning("[BuildingManager] 設定外觀失敗");
            return;
        }
        data.displayLevelCap = response.display_level_cap;
        UpdateVisual();
    }));
}
```

> ⚠️ **重要**：`[ContextMenu("...")]` 的字串裡**絕對不要用「/」**，Unity 會把它解讀成選單階層符號，
> 變成要點兩層的子選單，很容易讓人誤以為「點了沒反應」。用空格分隔就好。

### 🟡 中風險：改到既有方法，先看過同伴自己的版本再動手

**`BuildingManager.cs`** — `UpdateVisual()` 整個方法換成：

```csharp
public void UpdateVisual()
{
    if (data == null || data.stages == null || data.stages.Count == 0 || buildingImage == null)
        return;

    int effectiveLevel = data.displayLevelCap >= 0
        ? Mathf.Min(data.displayLevelCap, data.level)
        : data.level;

    int bestIndex = 0;
    int bestUnlockLevel = int.MinValue;

    for (int i = 0; i < data.stages.Count; i++)
    {
        BuildingLevelStage stage = data.stages[i];
        if (stage.unlockLevel <= effectiveLevel && stage.unlockLevel >= bestUnlockLevel)
        {
            bestUnlockLevel = stage.unlockLevel;
            bestIndex = i;
        }
    }

    data.selectedStageIndex = bestIndex;

    Sprite targetSprite = data.stages[bestIndex].visualSprite;
    if (targetSprite != null)
    {
        buildingImage.sprite = targetSprite;
    }
}
```

**`NetworkManager.cs`** — `Awake()` 裡，`DontDestroyOnLoad(gameObject);` 這行後面插入：

```csharp
#if UNITY_EDITOR
    // 在 Unity Editor 裡執行一定跟後端伺服器在同一台電腦，直接強制用 localhost，
    // 不用管 Inspector/LAN IP 設定。真機建置版本不會編到這段，還是用原本序列化的 serverUrl。
    serverUrl = "http://localhost:8000";
#endif
```

**`ExperienceManager.cs`** — ⚠️ **這裡最容易衝突**：如果同伴的 `ExperienceManager.cs` 已經有自己的
`Start()` 方法，同一個 class 不能有兩個 `Start()`（會編譯錯誤），要把
`SyncAllScenesFromServer();` 這一行**塞進他既有的 `Start()` 裡面**；完全沒有 `Start()` 才整個新增：

```csharp
private void Start()
{
    SyncAllScenesFromServer();
}

public void SyncAllScenesFromServer()
{
    if (UserSession.Instance == null || UserSession.Instance.userId == -1)
        return;
    int uid = UserSession.Instance.userId;
    StartCoroutine(NetworkManager.GetInstance().GetAllSceneStatus(uid, response =>
    {
        if (response == null || !response.success || response.scenes == null)
        {
            Debug.LogWarning("[ExperienceManager] 取得場景狀態失敗，建築外觀維持目前資料");
            return;
        }
        foreach (SceneStatus scene in response.scenes)
        {
            BuildingData target = allBuildings.Find(x => x.buildingType == scene.scene_id);
            if (target == null) continue;
            target.level = scene.scene_level;
            target.currentExp = scene.scene_exp;
            target.displayLevelCap = scene.display_level_cap;
        }
        foreach (BuildingManager manager in FindObjectsByType<BuildingManager>(FindObjectsSortMode.None))
        {
            manager.UpdateVisual();
        }
    }));
}
```

（這個方法需要 class 裡已經有 `public List<BuildingData> allBuildings;` 這個欄位，通常 `ExperienceManager`
本來就有，用來給既有的建築經驗值同步功能用。）

---

## Part 4：`BuildingData` 資產（`xxx_Data.asset`）的階段資料

**不要照抄我這邊的 GUID/fileID**——每台機器匯入圖片產生的 GUID 不同，照抄會直接參照到錯誤的圖或空的。
挑一棟建築（例如 `Farm_Data.asset`，Assets/Data/ 資料夾底下）測試，用 **Editor 操作**設定：

1. 準備至少 2 張想用的外觀圖片，匯入 Unity（拖進 `Assets/UI/` 之類的資料夾，Unity 會自動當成 Sprite）
2. 開啟 Game → 建築外觀管理 Building Stages（Part 2 建立的工具視窗）
3. 找到要設定的建築，`Stages` 列表按「+ 新增階段」，每一階填：
   - `unlockLevel`：這階需要場景等級幾才會解鎖，從 0 開始遞增（0、1、2...）
   - Sprite 欄位：**直接把圖片從 Project 視窗拖進去**（不要用文字手動寫參照，見「踩過的坑」）
4. `Level` 先設 1（新帳號的預設值一致）

---

## Part 5：⚠️ 給人類做的 Unity Editor 步驟

以下步驟需要滑鼠在 Unity Editor 裡操作，Claude 應該逐步引導使用者做，不要嘗試手動編輯
`.unity` 場景檔案的 UI 階層（Canvas/Panel/Button 這類物件）——原因見「踩過的坑」，
手動寫 YAML 建 UI 階層非常容易出錯且難以排查。

### 5.1 建立選項按鈕 Prefab

1. Hierarchy 空白處右鍵 → `UI` → `Button - TextMeshPro`（第一次用會跳出 Import TMP Essentials，按 Import）
2. 改名叫 `StageOption`
3. `Add Component` → `Building Stage Option Button`
4. 三個欄位這樣拖：
   - `Icon Image` ← 拖自己的 `Image (Script)` 元件
   - `Label Text` ← 拖底下子物件 `Text (TMP)`
   - `Button` ← 拖自己的 `Button (Script)` 元件
5. 拖到 Project 視窗的 `Assets/Prefab/` 存成 Prefab，場景裡的可以刪掉
6. **驗證**：完成後打開這個 `.prefab` 檔案讀取內容，確認
   `BuildingStageOptionButton` 元件的 `iconImage`/`labelText`/`button` 三個欄位都**不是** `{fileID: 0}`
   （這是本次開發過程中真的發生過的 bug：欄位以為拖了，實際上是空的）

### 5.2 建立外觀選擇視窗本體

1. Hierarchy 右鍵 `Canvas` → `UI` → `Panel`，改名 `BuildingStagePicker`
2. 上面右鍵 → `UI` → `Panel`（再一個，當容器），改名 `ContentPanel`，加 `Horizontal Layout Group`
3. 上面右鍵 → `UI` → `Text - TextMeshPro`，改名 `Title`
4. 上面右鍵 → `UI` → `Button - TextMeshPro`，改名 `CloseButton`，文字改「關閉」
5. `BuildingStagePicker` 加 `Building Stage Picker Panel` 元件：
   - `Panel Root` ← 自己
   - `Content Parent` ← `ContentPanel`
   - `Option Button Prefab` ← 5.1 存的 Prefab
   - `Title Text` ← `Title`
6. `CloseButton` 的 `On Click ()` 加一項：物件拖 `BuildingStagePicker`，方法選 `Hide()`
7. **建議**：把 `BuildingStagePicker` 也拖成 Prefab（存到 `Assets/Prefab/`），下次要在其他場景用可以直接拖，不用重搭

### 5.3 接上某棟建築的點擊

1. 選這棟建築的物件，`Add Component` 加 `Building Manager`：
   - `Data` ← 對應的 `xxx_Data.asset`
   - `Building Image` ← 這個物件自己的 `Image` 元件
2. 該物件的 `Button` 元件 `On Click ()`：如果有指到會報錯的舊方法（例如 `NavigateToScene()` 指到不存在的場景），移除它
3. 新增一項：物件拖自己，方法選 `BuildingManager` → `OpenStagePicker()`

### 5.4 建立自動登入測試物件

1. Hierarchy 空白處右鍵 → `Create Empty`，改名 `EditorAutoLogin`
2. `Add Component` 加 `Editor Auto Login`（帳密留預設 `editor_test`/`test1234`，或改成你們自己約定的）

### 5.5 存檔！

改完全部要 **Ctrl+S** 存場景。按 Play 前如果跳出「Scene(s) Have Been Modified」，一定要點 **Cancel**
先存檔，絕對不要點「Discard Unsaved Scenes」（會把上面辛苦搭的東西全部復原消失）。

---

## Part 6：踩過的坑（務必看過，避免重蹈覆轍）

1. **Sprite 欄位手動用文字寫參照，Unity 顯示「Missing (Sprite)」**
   原因：直接寫 `{fileID: X, guid: Y, type: 3}` 這種純文字參照，Unity 有時候不會正確重新解析。
   解法：一律用滑鼠把圖片從 Project 視窗拖進欄位，不要手寫。

2. **`[ContextMenu("A / B")]` 點了沒反應**
   原因：字串裡的「/」被當成選單階層符號，變成兩層子選單。
   解法：字串裡不要放「/」。

3. **Prefab 裡的欄位「看起來」拖了，實際上是空的**
   原因：在 Play 模式時展開場景裡動態生成的物件、去改那個實例的欄位——那些改動不會存回 Prefab 資產，
   一停止 Play 就消失。
   解法：一定要**雙擊 Project 視窗裡的 Prefab 資產**進入 Prefab 編輯模式改，不是改場景裡跑出來的實例。

4. **`Request timeout`，`NetworkManager.serverUrl` 連不到**
   原因：這個欄位預設值可能是別人電腦的 LAN IP。
   解法：本文件 Part 3 已經加了 Editor 內強制用 `localhost` 的判斷，記得同伴電腦上也要跑一份後端伺服器
   （`uvicorn main:app --port 8000`，在 `recipe-app` 資料夾下執行，且要讓它保持執行）。

5. **選了一個階段，後端回 400 `display_level 必須介於 0 到 X 之間`**
   這不是 bug，是後端正確擋下「這個帳號實際上還沒解鎖到這麼高」的請求（可能是 Unity 本地 `data.level`
   還沒跟伺服器同步完就先讓使用者點了）。不需要修改，這代表安全機制設計正確。

---

## Part 7：測試驗證清單

1. `psql` 跑過 `schema_tasks.sql`，後端伺服器 `uvicorn main:app --port 8000` 有在跑
2. 資料庫裡有測試帳號（跟 `EditorAutoLogin.cs` 裡設定的帳密一致）
3. Unity 按 Play → Console 出現 `[EditorAutoLogin] 已自動登入測試帳號`
4. 點掛了 `BuildingManager` 的建築 → 跳出外觀選擇視窗，列出的選項數量等於「已解鎖階段數」
5. 選一個選項 → Console 出現 `[BuildingManager] xxx UpdateVisual：level=..., bestIndex=..., targetSprite=...`，
   `targetSprite` 不是 `null`，畫面上的圖真的換了
6. （選用）用 `curl` 手動打 20 次 `/api/npc/task/complete` 模擬升級，確認 `leveled_up: true` 時
   `completion_count` 歸零、`scene_level +1`、`display_level_cap` 被清空
