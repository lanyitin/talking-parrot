## Context

`talking-parrot` 是一個跨平台（Windows/Linux/macOS）的影音轉錄 CLI，採用「外部 YAML 設定驅動」的多階段 Pipeline 架構（詳見 `docs/architecture/pipeline-overview.md`）。整體架構共有五個 Stage：VAD、Chunking、Transcription、Alignment、PostProcessing，並透過工廠模式注入平台相關後端（faster-whisper 對 Windows/Linux、mlx-whisper 對 macOS；EnglishAlignment / JapaneseAlignment 對應 word/character 粒度）。

目前 `src/talking_parrot/` 僅有空 `__init__.py`，無任何實作。本 change 的目標是建立所有 Stage 共用的基礎建設，以便後續每個 Stage 都能以獨立 change 並行實作而互不阻塞。

關鍵架構約束：
- **SOLID/12-Factor**：所有 Stage 依賴抽象介面而非具體實作；設定來自外部 YAML；中間狀態存於 `PipelineContext`，Stage 本身無狀態。
- **跨平台**：核心模組不能 import `mlx_whisper` 或 `faster_whisper`；ML 後端只能在工廠的條件分支裡 import。
- **音訊不入 Context**：`Chunk` 不持有 PCM bytes，所有需要音訊的下游 Stage 透過 `AudioReader` 以 `(start_ms, end_ms)` 懶讀，避免大量 PCM 進入 `PipelineContext`。
- **安全表達式求值**：YAML 中的 `vad.formula` 與 `transcribing[].condition` 必須走白名單 AST walker，嚴禁 `eval()` / `exec()`。

## Goals / Non-Goals

**Goals:**

- 提供 Stage 實作可直接依賴的穩定資料模型與抽象介面，使後續 Stage changes 不需要回頭修改 foundation。
- 所有 cross-cutting 機制（Context 傳遞、設定驗證、音訊懶讀、表達式求值安全策略、JSON 序列化）只實作一次。
- 端對端 smoke flow（CLI 載入 config → 計算 hash → 跑空 stage 序列 → 輸出空 ProjectFile JSON）可執行成功，作為後續 Stage 的整合測試起點。
- pyproject.toml 依賴宣告以「平台共用 vs. 平台選用」明確分群（Factor II）。

**Non-Goals:**

- 不實作任何 Stage 的具體邏輯，也不載入任何 ML 模型。
- 不處理 SRT/WebVTT 輸出格式（屬於後續 export change）。
- 不整合 regression test 框架（TODOs.md 第一項，獨立 change）。
- 不處理多檔批次處理；本 change 只支援「單檔輸入」CLI 路徑。
- 拒絕：把 audio bytes 放進 `Chunk` 或 `PipelineContext`（會撐爆 long-form 影片的記憶體）。
- 拒絕：用 Python `eval()` 求值 YAML 表達式（安全風險）。

## Decisions

### Use frozen dataclasses for PipelineContext and shared models

選用 `@dataclass(frozen=True)` 搭配 `dataclasses.replace()` 而非 `pydantic.BaseModel` 用於 `PipelineContext` 與所有共享資料模型。`PipelineConfig` 系列因需要 YAML 驗證，採用 `pydantic.BaseModel`。

理由：`PipelineContext` 在 Stage 之間以「不可變傳遞物件」流動，frozen dataclass 提供結構化複製與型別檢查；pydantic 的驗證開銷對 hot-path 物件多餘。設定檔來源於外部 YAML，pydantic 的驗證能力不可替代。

替代方案：全部用 pydantic（驗證開銷高、Stage 間複製語意不自然）；全部用 dataclass（YAML 載入需自行寫驗證，重複造輪子）。

### AudioReader as injected service with LRU caching

`AudioReader` 是介面（`Protocol` 或 `abc.ABC`），預設實作 `FfmpegAudioReader` 在建構時綁定單一 `file_path`，內部以 `functools.lru_cache(maxsize=N)` 快取最近 N 個 `(start_ms, end_ms)` 區間。在 CLI 入口建構並注入給 `TranscriptionStage` 與 `AlignmentStage`。

理由：避免在 `PipelineContext` 中保留所有 PCM；LRU 快取讓相鄰 chunk 重疊讀取（例如 alignment 緊跟在 transcription 之後對同一 chunk 操作）只解碼一次。介面化讓測試可注入 in-memory fake reader。

替代方案：把 audio bytes 直接放進 `Chunk` — 對 1 小時影片估算約 200MB+ PCM，會導致 Context 物件體積失控；每次 stage 自行呼叫 ffmpeg — 重複解碼浪費 CPU。

### SafeExpressionEvaluator base with Python ast module

`SafeExpressionEvaluator` 使用標準函式庫 `ast` 模組解析表達式，在 walker 中只允許白名單節點類型；遇到 `Call`、`Attribute`、`Subscript`、`Lambda` 等節點直接拋 `ExpressionError`。子類別（`FormulaEvaluator`、`ConditionEvaluator`）透過覆寫 `allowed_operators` 與 `allowed_literal_types` 屬性收緊白名單。

理由：標準函式庫零依賴，AST 白名單的攻擊面遠小於 `eval()` 或 `asteval`。本身不引入第三方執行環境。

替代方案：`asteval` 第三方套件（仍引入額外依賴，且歷史上有 sandbox bypass CVE）；`eval()` 直接禁用（安全紅線）。

### CLI entry point assembles dependencies; no service locator

`talking_parrot.cli:main` 是唯一知道具體後端類別的位置：讀環境變數 → 用 `TranscriptionBackendFactory.create()` 與 `AlignmentBackendFactory` 取得後端 → 建構 `FfmpegAudioReader` → 建構各 Stage 並依序傳給 `PipelineOrchestrator`。Stage 與 orchestrator 完全不知道工廠或具體類別。

理由：DIP — 高層模組（Stage、Orchestrator）依賴抽象，具體裝配只在 entry point 一處。便於測試替身注入。本 change 中 Stage 為空殼或尚未存在，但裝配框架先到位，後續 Stage change 只需在 cli.py 加一行注入。

替代方案：service locator pattern（隱藏依賴、難測試）；Stage 自行 import 具體後端（破壞 DIP）。

### Five capabilities split aligned with module boundaries

將 foundation 拆成五個 capability：`pipeline-foundation`（Stage 介面 + Context + Orchestrator）、`pipeline-config`、`pipeline-data-models`、`audio-io`、`safe-expression`。每個 capability 對應 spec 檔，spec 中的 requirements 直接映射到對應 module 的契約。

理由：spec 邊界與程式碼模組邊界對齊，後續 Stage change 在新增 spec 或修改既有 spec 時不會跨多個概念領域。粒度避免單一 spec 過大。

替代方案：單一 `foundation` capability（spec 過長、違反單一概念）；十個以上細碎 capability（過度切分）。

### pyproject.toml optional-dependencies for platform backends

核心 `[project.dependencies]` 包含 `pydantic`、`pyyaml`、`ffmpeg-python`、`structlog`；`[project.optional-dependencies.faster-whisper]` 與 `[project.optional-dependencies.mlx]` 各自宣告平台後端；`[project.optional-dependencies.dev]` 含 `pytest`、`mypy`、`ruff`。

理由：使用者依平台選裝（Factor II 明確宣告），避免在 Linux 機器上嘗試裝 `mlx-whisper`（mlx 僅 macOS / Apple Silicon 可用）。

替代方案：把全部後端列為核心依賴（macOS 上裝 `faster-whisper` 仍可工作但浪費；Linux 上裝 `mlx` 直接安裝失敗）。

## Risks / Trade-offs

- **[Risk] AudioReader LRU 快取大小調校困難** → Mitigation: 預設 `maxsize=4`（足以覆蓋「transcription→alignment 對同一 chunk」的窗口），並透過 `MODEL_CACHE_DIR` 之外另列 `AUDIO_CACHE_SIZE` 環境變數允許覆寫；後續若實測有問題可改為 byte-budget LRU。
- **[Risk] frozen dataclass 與 List 欄位互動** → Mitigation: `PipelineContext` 中所有 `List[...]` 欄位約定為「整批替換」（用 `dataclasses.replace(ctx, vad_segments=new_list)`），不允許就地 `append`；以 `tuple` 而非 `list` 在型別簽章上強制此約定可選但暫不採用以保留 IDE 友善度。
- **[Risk] 安全表達式 walker 漏掉某種 AST 節點** → Mitigation: 採「預設 deny、白名單 allow」策略；`_visit` 預設 `raise ExpressionError`，子類別只能加白節點不能改預設；單元測試列舉所有危險節點（`Call`、`Attribute`、`Lambda`、`ListComp`、`Subscript`、`Import`、`Assign`）並斷言全部被拒絕。
- **[Risk] foundation 與後續 Stage change 間的契約變動** → Mitigation: spec 中明確列出每個介面與資料結構的 SHALL 條款；任何後續 change 若需修改介面，必須以 modified capability 形式進入該 spec 的 delta，避免無聲改動破壞下游。
- **[Trade-off] 本 change 不實際完成任何使用者可見功能** → 接受。foundation change 的價值在於「讓後續 N 個 Stage change 並行展開」，而非自身可 demo。CLI smoke flow（空 stage 序列輸出空 ProjectFile）作為最低可驗證證據。
- **[Trade-off] 五個 capability 對單一 change 略多** → 接受。寧可 spec 邊界與 module 邊界對齊，避免後續 Stage change 為了保持 spec 一致性而被迫膨脹。
