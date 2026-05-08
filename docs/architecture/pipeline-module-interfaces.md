---
title: Pipeline 模組介面設計
tags:
  - architecture
  - interface
  - pipeline
aliases:
  - 模組介面設計
---

# Pipeline 模組介面設計

本文以語言無關的偽型別定義每個模組的介面（輸入、輸出、方法簽章）。Python 實作時對應為 `abc.ABC` + `@abstractmethod`。

---

## 1. 核心抽象介面

### 1.1 PipelineStage（所有 Stage 的共同介面）

```
interface PipelineStage:
    name: str  (read-only property)

    process(ctx: PipelineContext) -> PipelineContext
        # 接收當前 context，執行本 Stage 的工作，
        # 回傳附加本 Stage 輸出的新 context。
        # 若 Stage 在設定中被停用，應原封不動回傳 ctx。
```

> **ISP 說明**：不同 Stage 之間沒有共用「特殊方法」，只共享最小的 `process()` 介面，避免 fat interface。

---

### 1.2 VADBackend

```
interface VADBackend:
    name: str  (read-only property)

    analyze(audio_data: bytes, sample_rate: int) -> List[RawVadFrame]
        # 逐幀分析音訊，回傳每幀的語音機率原始值。
        # 呼叫方（VADStage）負責根據 formula 合成多個 Backend 的結果。
```

```
RawVadFrame
├── time_ms: int      # 此幀的起始時間
└── prob: float       # 此 Backend 判斷為語音的機率 (0.0 ~ 1.0)
```

> 實作：`TenVADBackend`、`SileroVADBackend`。
> **LSP 說明**：`VADStage` 只呼叫 `analyze()`，不需要知道是哪個 Backend。

---

### 1.3 SafeExpressionEvaluator（共用基底）

```
interface SafeExpressionEvaluator:
    evaluate(expression: str, variables: Dict[str, Any]) -> Any
        # 對來自 YAML 設定的字串表達式求值，
        # 並由實作以白名單 AST walker 限制可用語法（嚴禁 eval/exec）。
        # 若引用未定義識別字、使用未授權節點、或語法錯誤，拋出 ExpressionError。

    allowed_operators: Set[OperatorKind]   (read-only property)
        # 子類別宣告允許的運算子集合（算術、比較、邏輯）。
    allowed_literal_types: Set[Type]       (read-only property)
        # 允許的字面值型別（例如 {int, float} 或 {bool}）。
```

> **安全策略一致性**：所有「對 YAML 字串求值」的元件皆繼承此介面，確保 `formula` 與 `condition` 走同一套安全機制。實作可內部使用 Python `ast` 模組或第三方套件（如 `asteval`），但介面層嚴禁暴露 `eval()` / `exec()`。

### 1.3.1 FormulaEvaluator

```
interface FormulaEvaluator extends SafeExpressionEvaluator:
    # 專用於 VAD composite score 的浮點表達式求值。
    # variables 限定為 Dict[str, float]；回傳 float。
    # 例：formula="(ten_vad_prob * 0.9) + (silero_vad_prob * 0.1)"
    #     variables={"ten_vad_prob": 0.95, "silero_vad_prob": 0.82}
    #
    # allowed_operators = {ADD, SUB, MUL, DIV, USUB}
    # allowed_literal_types = {int, float}
```

---

### 1.4 TranscriptionBackend

```
interface TranscriptionBackend:
    platform: str  (read-only property)  # 例："faster-whisper", "mlx-whisper"

    transcribe(
        audio_data: bytes,
        sample_rate: int,
        model_name: str,
        language_hint: str | None
    ) -> RawTranscriptionOutput
        # 對音訊片段執行轉錄，回傳原始輸出。
        # 若模型尚未載入，在此方法內懶加載並快取。
```

```
RawTranscriptionOutput
├── text: str
├── language: str
├── avg_logprob: float
├── compression_ratio: float
├── no_speech_prob: float
└── segments: List[RawSegment]     # 後端原生的片段分割（供 word-timestamp 使用）
```

> 實作：`FasterWhisperBackend`（Windows/Linux）、`MLXWhisperBackend`（macOS）。
> 選擇邏輯封裝在 `TranscriptionBackendFactory` 內，不在 Stage 內部。

---

### 1.5 ConditionEvaluator

```
interface ConditionEvaluator extends SafeExpressionEvaluator:
    evaluate(condition: str, metrics: TranscriptionMetrics) -> bool
        # 將 condition 字串對 metrics 物件求值，回傳布林值。
        # variables 由 metrics 的欄位名稱與當前值組成。
        # 特殊值："true" 永遠回傳 True，"false" 永遠回傳 False。
        # 若語法錯誤或引用未定義欄位，拋出 ConditionError（ExpressionError 子類別）。
        #
        # allowed_operators = {LT, GT, LE, GE, EQ, NE, AND, OR, NOT}
        # allowed_literal_types = {int, float, bool}
```

> 與 `FormulaEvaluator` 共用 `SafeExpressionEvaluator` 基底，確保安全策略一致。詳細語法規則與評估時機見 [[ADR-0002-condition-評估器]]。

---

### 1.6 AlignmentGranularity（列舉）

```
enum AlignmentGranularity:
    WORD       # 詞級別對齊，適用英文等以空格分隔詞彙的語言
    CHARACTER  # 字元級別對齊，適用日文等無空格分隔的語言
```

> **用途**：`AlignmentBackend` 將此值透過屬性對外暴露，`GranularityAwareProcessorFactory` 讀取此值後決定選用哪組 `SubtitleProcessor`。`AlignmentGranularity` 同時也是 `PostProcessingStage` 的策略選擇鍵，是 Alignment 層與 Post-Processing 層之間的唯一耦合點。

---

### 1.7 AlignmentBackend

```
interface AlignmentBackend:
    language: str                        (read-only property)
        # 此後端所服務的語言，例："en"、"ja"。
    granularity: AlignmentGranularity    (read-only property)
        # 此後端的對齊粒度，供下游 PostProcessingStage 使用。

    align(
        audio_data: bytes,
        sample_rate: int,
        transcript: str
    ) -> AlignmentResult
        # 對音訊與轉錄文字執行 forced alignment。
        # 回傳含逐字（或逐字元）時間戳記的 AlignmentResult。
        # 若模型尚未載入，在此方法內懶加載並快取。
        # 語言由 backend.language 屬性決定，呼叫方不再重複傳入。
```

```
AlignmentResult
├── granularity: AlignmentGranularity
└── tokens: List[AlignedToken]

AlignedToken
├── text: str           # 詞（英文）或字元（日文）
├── start_ms: int
└── end_ms: int
```

> 實作：`EnglishAlignmentBackend`（granularity=WORD）、`JapaneseAlignmentBackend`（granularity=CHARACTER）。
> 選擇邏輯封裝在 `AlignmentBackendFactory` 內，`AlignmentStage` 只依賴 `AlignmentBackend` 介面。
> **LSP 說明**：兩個實作皆可被透明替換，呼叫方不需 isinstance 判斷。

---

### 1.8 AudioReader

```
interface AudioReader:
    sample_rate: int   (read-only property)   # 解碼輸出的取樣率（通常與 MediaInfo 一致）

    read(start_ms: int, end_ms: int) -> bytes
        # 讀取指定時間區間的音訊位元組（PCM）。
        # 實作通常以 ffmpeg 解碼，並可在內部對連續區間做 LRU 快取。
        # 同一個 AudioReader 實例綁定單一影音檔（建構時注入 file_path）。
```

> **動機**：`Chunk` 不持有 audio bytes，所有需要音訊的 Stage（`TranscriptionStage`、`AlignmentStage`）皆透過注入的 `AudioReader` 懶讀，避免在 `PipelineContext` 內保留大量 PCM。
> **DIP 說明**：Stage 依賴 `AudioReader` 介面，具體實作（ffmpeg 包裝）在 `cli.py` 建立並注入。

---

### 1.9 SubtitleExporter

```
interface SubtitleExporter:
    format_name: str  (read-only property)  # 例："srt", "webvtt"
    file_extension: str  (read-only property)  # 例：".srt", ".vtt"

    export(subtitles: List[Subtitle], output_path: str) -> None
        # 將字幕序列序列化為對應格式並寫入 output_path。
```

> 實作：`SRTExporter`、`WebVTTExporter`。

---

### 1.10 ProjectFileWriter

```
interface ProjectFileWriter:
    write(project_file: ProjectFile, output_path: str) -> None
        # 將 ProjectFile 序列化為 JSON 並寫入 output_path。
```

> 此為單一具體實作（無需介面繼承），但仍以介面形式定義以支援未來擴充（例如寫入資料庫）。

---

## 2. 工廠介面

### 2.1 AlignmentBackendFactory

```
class AlignmentBackendFactory:
    create(
        language: str,
        granularity_pref: GranularityPreference = AUTO
    ) -> AlignmentBackend
        # 根據 (語言, 粒度偏好) 回傳對應的 AlignmentBackend 實作。
        # 內部維護 (language, granularity) -> backend_class 的二維註冊表。
        #
        # 路由規則：
        #   granularity_pref == AUTO  : 使用該語言的預設 backend
        #     - "en" -> EnglishAlignmentBackend       (granularity=WORD)
        #     - "ja" -> JapaneseAlignmentBackend      (granularity=CHARACTER)
        #   granularity_pref == WORD/CHARACTER : 強制使用對應粒度的 backend
        #     例：("ja", WORD) 將來若註冊了 JapaneseWordAlignmentBackend (MeCab 斷詞 + word-level wav2vec2) 即可選用
        #
        # - (語言, 粒度) 組合無對應 backend  -> 拋出 UnsupportedAlignmentBackendError
        # - 環境變數 ALIGNMENT_BACKEND_<LANG> 仍可覆蓋（供測試與部署環境臨時切換）。
```

> **DIP 說明**：`AlignmentStage` 只依賴 `AlignmentBackend` 介面；`AlignmentBackendFactory` 在應用程式入口點被呼叫，並以建構子注入到 Stage。
> **OCP 說明**：新增語言只需新增一個 `AlignmentBackend` 實作與工廠內的一條路由規則，不修改 Stage 或現有後端。

---

### 2.2 GranularityAwareProcessorFactory

```
interface GranularityAwareProcessorFactory:
    create(granularity: AlignmentGranularity | None) -> List[SubtitleProcessor]
        # 依粒度回傳有序的 SubtitleProcessor 清單：
        #   - WORD       -> [WordBoundaryMergeProcessor, WordBoundarySplitProcessor]
        #   - CHARACTER  -> [CharacterBoundaryMergeProcessor, CharacterBoundarySplitProcessor]
        #   - None       -> [TimeBasedMergeProcessor, TimeBasedSplitProcessor]  (fallback)
        # None 代表 alignment 未啟用，fallback 到純時間基礎實作。
```

> **OCP 說明**：新增粒度類型（例如 `SYLLABLE`）只需在 enum 與工廠新增分支，不修改 PostProcessingStage。
> **DIP 說明**：`PostProcessingStage` 依賴 `GranularityAwareProcessorFactory` 介面，具體工廠由入口點注入。

---

### 2.3 SubtitleExporterFactory

```
class SubtitleExporterFactory:
    create(format_name: str) -> SubtitleExporter  (classmethod)
        # 依 format_name 回傳對應的 SubtitleExporter 實作。
        # 已知映射：
        #   "srt"    -> SRTExporter
        #   "webvtt" -> WebVTTExporter
        # 未知 format_name 拋出 ValueError。
```

> 此工廠由 `cli.py` 在輸出階段呼叫，不注入到任何 Stage，只在 Orchestrator 完成後由 CLI 層使用。

---

### 2.4 TranscriptionBackendFactory

```
class TranscriptionBackendFactory:
    create() -> TranscriptionBackend
        # 根據執行時的作業系統或環境變數，
        # 回傳適合當前平台的 TranscriptionBackend 實作。
        # 判斷邏輯：
        #   - TRANSCRIPTION_BACKEND 環境變數（優先）
        #   - sys.platform: "darwin" -> MLXWhisperBackend
        #   - sys.platform: "win32" / "linux" -> FasterWhisperBackend
```

> **DIP 說明**：`TranscriptionStage` 只依賴 `TranscriptionBackend` 介面，`TranscriptionBackendFactory` 在應用程式入口點建立，並以建構子注入到 Stage 中。

---

### 2.5 Policy 介面（後處理策略注入點）

後處理 Split 系列的 Processor 接受兩種可注入的 Policy 物件，讓拆行的「文字切點」與「時間戳記切點」邏輯可被獨立替換（OCP）。

#### SplitBoundaryPolicy（文字切點 Policy）

```
protocol SplitBoundaryPolicy:
    adjust(text: str, candidate_index: int, search_radius: int) -> int
        # 接受字幕文字、線性內插得到的候選切點（字元 index），
        # 以及搜尋半徑（字元數）。
        # 回傳調整後的切點，必須在 [1, len(text) - 1] 範圍內。
        # 實作必須為純函式，不得修改 text。
```

| 實作 | 行為 |
|------|------|
| `LinearSplitBoundaryPolicy` | 直接回傳 `candidate_index`（預設、無語言假設） |
| `JapaneseSplitBoundaryPolicy` | 在 `search_radius` 內尋找符合日文語法規則的切點（不切助動詞、詞尾活用等）；找不到合法切點時退回 `candidate_index` |

#### SplitTimePolicy（時間切點 Policy）

```
protocol SplitTimePolicy:
    adjust(candidate_ms: int, cue_start_ms: int, cue_end_ms: int) -> int
        # 接受線性內插的候選時間戳（ms）與字幕的時間區間。
        # 回傳調整後的時間戳，必須嚴格在 (cue_start_ms, cue_end_ms) 內。
        # 實作必須為純函式。

    pick(cue_start_ms: int, cue_end_ms: int) -> int | None
        # 在 cue 時間區間內尋找最佳靜音中點。
        # 若無合適靜音段，回傳 None。
        # 實作必須為純函式。
```

| 實作 | 行為 |
|------|------|
| `LinearSplitTimePolicy` | `adjust` 直接回傳 `candidate_ms`；`pick` 永遠回傳 `None`（預設） |
| `VadAlignedSplitTimePolicy` | 建構時注入 VAD 靜音清單與搜尋半徑；`adjust` 在候選點附近找最近靜音中點；`pick` 回傳 cue 內最佳靜音中點（VAD driven 主路徑） |

> **DIP 說明**：`CharacterBoundarySplitProcessor`、`WordBoundarySplitProcessor`、`TimeBasedSplitProcessor` 皆依賴這兩個 Protocol 的抽象，具體實作由 `GranularityAwareProcessorFactory` 在建構 Processor 時注入。

---

## 3. 各 Stage 詳細介面

### 3.1 VADStage

```
class VADStage implements PipelineStage:
    __init__(
        backends: List[VADBackend],       # 注入，支援一或多個
        formula_evaluator: FormulaEvaluator  # 注入
    )

    process(ctx: PipelineContext) -> PipelineContext
        # 若 ctx.config.vad.enabled == False，直接回傳 ctx。
        # 1. 呼叫每個 backend.analyze() 取得各幀原始機率
        # 2. 以 formula_evaluator 計算每幀 composite_score
        # 3. 依 activity_threshold、min/max duration 規則合併為 VadSegment
        # 4. 套用 speech_pad_ms 擴展每個 Segment 的邊界
        # 5. 回傳 ctx with vad_segments=<結果>
```

### 3.2 ChunkingStage

```
class ChunkingStage implements PipelineStage:
    __init__()  # 無外部依賴；不需要 AudioReader（不再持有 audio bytes）

    process(ctx: PipelineContext) -> PipelineContext
        # 若 ctx.config.chunking.enabled == False，將所有 VadSegment 視為單一 Chunk
        # （仍套用步驟 3 的硬切兜底）。
        # 1. 以貪婪演算法將連續 VadSegment 合併，直到 max_chunk_seconds 上限
        # 2. 在 Chunk 邊界加入 silence_pad_seconds（僅延伸時間區間，不截取音訊）
        # 3. 兜底硬切：若任一 Chunk 區間 (end_ms - start_ms) > max_chunk_seconds * 1000，
        #    依時間平均切成多個 Chunk，並寫 WARNING log 提示「切割點可能落在詞中間，
        #    建議調整 vad.max_speech_duration_ms 與 chunking.max_chunk_seconds 對應關係」
        # 4. 回傳 ctx with chunks=<結果>（每個 Chunk 僅含時間區間，不含 audio_data）
```

> **超長處理策略**：`ConfigLoader` 在載入時若偵測到 `vad.max_speech_duration_ms > chunking.max_chunk_seconds * 1000`，應寫 WARNING 日誌（不視為錯誤——VAD 可能停用）。`ChunkingStage` 的硬切是執行期兜底，確保下游 backend 不會收到超出處理上限的音訊。

### 3.3 TranscriptionStage

```
class TranscriptionStage implements PipelineStage:
    __init__(
        backend: TranscriptionBackend,       # 注入
        condition_evaluator: ConditionEvaluator,  # 注入
        audio_reader: AudioReader            # 注入；以 chunk.start_ms/end_ms 懶讀音訊
    )

    process(ctx: PipelineContext) -> PipelineContext
        # 對每個 Chunk（詳細評估流程見 ADR-0002）：
        # 0. 透過 audio_reader.read(chunk.start_ms, chunk.end_ms) 取得 audio bytes
        # 1. 初始化空的 metrics（所有欄位為 None）
        # 2. 依序遍歷 TranscribingStep：
        #    a. 對「目前的 metrics」評估 step.condition
        #    b. 若為 True：以 step.model 呼叫 backend.transcribe(audio_bytes, ...)，
        #       並用回傳的 metrics 更新狀態
        #    c. 若為 False：跳過此 step
        # 3. 以最後一次成功轉錄的結果組裝 TranscriptionResult 並累積
        # 回傳 ctx with transcription_results=<結果>
```

> **注意**：第一個 step 必須使用 `condition: true`，因為初始 metrics 為空，任何引用欄位的表達式都會拋出 `ConditionError`。後續 step 的 condition 以前一次轉錄的 metrics 為基準，達成「級聯升級」效果。詳細評估流程見 [[ADR-0002-condition-評估器]]。

### 3.4 HallucinationFilterStage

```
class HallucinationFilterStage implements PipelineStage:
    __init__(config: HallucinationFilterConfig)

    process(ctx: PipelineContext) -> PipelineContext
        # 若 config.enabled == False，直接回傳 ctx（transcription_results 不變）。
        # 若 enabled == True，過濾 ctx.transcription_results 中符合以下任一規則的結果：
        #   1. 精確短語匹配：text.strip() 完全等於 known_hallucination_phrases 中任一項
        #   2. 括號文字：整段 text 被括號包圍（ASCII 或全形括號）
        #   3. 長重複字元：包含 5 個以上連續相同非空白字元
        #   4. 低 logprob + 高 no_speech_prob：同時滿足兩個指標閾值
        #   5. 高壓縮比：compression_ratio 超過設定閾值
        #   6. 高重複率：repetition_ratio 超過設定閾值
        # 保留其餘結果的相對順序，回傳新的 PipelineContext。
```

> **SRP 說明**：HallucinationFilter 只負責品質過濾，不做任何文字修改或時間調整，符合單一職責。
> **OCP 說明**：每條過濾規則有獨立的 enabled flag，新增規則只需擴充 `HallucinationFilterConfig`，不修改 Stage 邏輯。

---

### 3.5 AlignmentStage

```
class AlignmentStage implements PipelineStage:
    __init__(
        backend_factory: AlignmentBackendFactory,  # 注入
        audio_reader: AudioReader                  # 注入；以 chunk.start_ms/end_ms 懶讀音訊
    )

    process(ctx: PipelineContext) -> PipelineContext
        # 若 ctx.config.align.enabled == False，回傳 ctx with
        #   alignment_status=DISABLED, alignment_granularity=None, alignment_results=[]。
        #
        # 1. 以 (ctx.config.expected_language, ctx.config.align.granularity) 呼叫
        #    backend_factory.create() 取得後端；若無對應 backend，記錄 FAILED 並回傳。
        # 2. 對每個 TranscriptionResult：
        #    a. 以 result.chunk_index 反查 ctx.chunks[i] 取得時間區間
        #    b. 呼叫 audio_reader.read(chunk.start_ms, chunk.end_ms) 取得音訊
        #    c. 呼叫 backend.align(audio_bytes, audio_reader.sample_rate, result.text)
        #    d. 將回傳的 AlignedToken 清單填入該 TranscriptionResult.aligned_tokens
        # 3. 將所有 AlignmentResult 與 backend.granularity 寫入 PipelineContext
        # 4. 回傳 ctx with
        #    alignment_status=SUCCESS, alignment_results=<結果>, alignment_granularity=<granularity>
        #
        # 任何步驟拋出例外時，記錄為 alignment_status=FAILED 並寫 WARNING log，
        # 下游 PostProcessingStage 將 fallback 到 TimeBasedProcessor。
```

> **DIP 說明**：`AlignmentStage` 只依賴 `AlignmentBackendFactory` 介面，不知道具體語言後端。
> **SRP 說明**：語言路由邏輯完全封裝在 `AlignmentBackendFactory`，Stage 不含任何語言判斷。

### 3.5 PostProcessingStage

```
class PostProcessingStage implements PipelineStage:
    __init__(
        processor_factory: GranularityAwareProcessorFactory  # 注入
    )

    process(ctx: PipelineContext) -> PipelineContext
        # 1. 讀取 ctx.alignment_granularity（可為 WORD、CHARACTER，或 None）
        # 2. 呼叫 processor_factory.create(granularity) 取得有序的 processor 清單
        # 3. 將 TranscriptionResult 轉換為初始 Subtitle 序列
        # 4. 依序通過每個 SubtitleProcessor
        # 5. 回傳 ctx with subtitles=<最終結果>
```

```
interface SubtitleProcessor:
    process(subtitles: List[Subtitle], config: PostProcessingConfig) -> List[Subtitle]
        # 單一後處理步驟。
        # 實作依粒度分為三組：
        #   WORD 組：WordBoundaryMergeProcessor、WordBoundarySplitProcessor
        #   CHARACTER 組：CharacterBoundaryMergeProcessor、CharacterBoundarySplitProcessor
        #   Fallback 組（alignment 未啟用）：TimeBasedMergeProcessor、TimeBasedSplitProcessor
```

**各 Processor 實作說明**

| Processor | 適用粒度 | 邏輯說明 |
|-----------|---------|---------|
| `WordBoundaryMergeProcessor` | WORD | 在詞邊界合併過短字幕，不跨詞切割 |
| `WordBoundarySplitProcessor` | WORD | 在詞邊界切分過長字幕 |
| `CharacterBoundaryMergeProcessor` | CHARACTER | 在字元邊界合併，適用無空格語言（日文） |
| `CharacterBoundarySplitProcessor` | CHARACTER | 在字元邊界切分，適用無空格語言（日文） |
| `TimeBasedMergeProcessor` | Fallback | 純依時間間隔合併，不依賴對齊資訊 |
| `TimeBasedSplitProcessor` | Fallback | 純依時間長度切分，不依賴對齊資訊 |

> **OCP 說明**：新增粒度類型只需實作對應的 `SubtitleProcessor` 群組並在工廠新增分支，不修改 Stage 或既有 Processor。
> **ISP 說明**：`SubtitleProcessor` 只暴露單一 `process()` 方法，不混入對齊資訊讀取或工廠邏輯。

---

## 4. 相關文件

- [[pipeline-overview|系統架構總覽]]
- [[pipeline-data-models|Pipeline 資料模型]]
- [[pipeline-post-processing-processors|後處理 Processor 家族]]
- [[ADR-0001-跨平台轉錄後端]]
- [[ADR-0002-condition-評估器]]
- [[ADR-0003-對齊粒度與後處理策略]]

相關 spec：[[../openspec/specs/alignment-backend/spec|alignment-backend]]、[[../openspec/specs/alignment-backend-factory/spec|alignment-backend-factory]]、[[../openspec/specs/transcription-backend/spec|transcription-backend]]、[[../openspec/specs/transcription-backend-factory/spec|transcription-backend-factory]]、[[../openspec/specs/vad-backend/spec|vad-backend]]、[[../openspec/specs/subtitle-exporter/spec|subtitle-exporter]]、[[../openspec/specs/subtitle-exporter-factory/spec|subtitle-exporter-factory]]、[[../openspec/specs/hallucination-filter-stage/spec|hallucination-filter-stage]]、[[../openspec/specs/split-boundary-policy/spec|split-boundary-policy]]、[[../openspec/specs/split-time-policy/spec|split-time-policy]]