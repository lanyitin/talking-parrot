## 1. 專案骨架與依賴宣告

- [x] 1.1 更新 `pyproject.toml`：依「pyproject.toml optional-dependencies for platform backends」決策，宣告核心依賴（pydantic、pyyaml、ffmpeg-python、structlog）與 `faster-whisper` / `mlx` / `dev` 三個 optional groups
- [x] 1.2 建立 `src/talking_parrot/` 子套件目錄骨架（`config/`、`models/`、`pipeline/`、`stages/`、`io/`、`expression/`）並新增空 `__init__.py`
- [x] 1.3 建立 `src/talking_parrot/logging_config.py`，依 `LOG_LEVEL` 環境變數初始化 structlog 寫入 stdout（Factor XI）

## 2. 共享資料模型（pipeline-data-models capability）

- [x] 2.1 依「Use frozen dataclasses for PipelineContext and shared models」決策，建立 `models/media.py`、`models/vad.py`、`models/chunk.py`（驗證 Chunk holds no audio bytes：欄位集合限定 index/start_ms/end_ms/source_segments）、`models/subtitle.py`，全部以 `@dataclass(frozen=True)` 宣告
- [x] 2.2 建立 `models/transcription.py`，定義 TranscriptionMetrics 與 TranscriptionResult exposes metrics for condition evaluation 所要求的欄位
- [x] 2.3 建立 `models/context.py`，依 PipelineContext fields 規格定義所有欄位與預設值；同時定義 AlignmentStatus enum has three states 與 AlignmentGranularity and GranularityPreference enums
- [x] 2.4 建立 `models/project_file.py`，遵守 ProjectFile is pure data 規格——僅含資料欄位，無自訂行為方法

## 3. 設定載入層（pipeline-config capability）

- [x] 3.1 建立 `config/models.py`：以 pydantic BaseModel 定義 PipelineConfig 系列；遵守 PipelineConfig sub-section optionality（vad/chunking/align/post_processing 為 Optional，transcribing 為非空 list）
- [x] 3.2 建立 `config/loader.py`，實作 ConfigLoader parses YAML into PipelineConfig 主流程；以 pydantic `extra="forbid"` 達成 ConfigLoader rejects unknown fields；於載入完成後檢查 First transcribing step condition must be "true"
- [x] 3.3 在 `ConfigLoader` 內加入 ConfigLoader warns on inconsistent VAD/chunking durations 規則：偵測 `vad.max_speech_duration_ms > chunking.max_chunk_seconds * 1000` 時以 structlog 寫 WARNING

## 4. 音訊與輸出 I/O（audio-io capability）

- [x] 4.1 建立 `io/media_hasher.py`，實作 MediaHasher computes SHA-256（streaming 雜湊，固定 chunk size，避免一次讀入整檔）
- [x] 4.2 依「AudioReader as injected service with LRU caching」決策，於 `io/audio_reader.py` 定義 AudioReader interface for lazy interval reads（read 方法的 ValueError 邊界條件）；於 `io/audio_decoder.py` 實作 Default AudioReader implementation uses ffmpeg with LRU cache（讀取 `AUDIO_CACHE_SIZE` 環境變數，預設 4）
- [x] 4.3 建立 `io/project_writer.py`，實作 ProjectFileWriter serializes ProjectFile to JSON（enum 以名稱序列化、ISO 8601 時間戳）

## 5. 安全表達式求值基底（safe-expression capability）

- [x] 5.1 依「SafeExpressionEvaluator base with Python ast module」決策，於 `expression/base.py` 定義 ExpressionError type hierarchy（ExpressionError、ConditionError、FormulaError）並實作 SafeExpressionEvaluator forbids eval and exec 與 Whitelist enforcement is default-deny 的 AST walker
- [x] 5.2 在 walker 中實作 ExpressionError on undefined identifiers，並透過 Subclass-declared whitelists（`allowed_operators`、`allowed_literal_types` 屬性）讓子類別收緊白名單
- [x] 5.3 建立 `expression/formula.py` 與 `expression/condition.py` 介面殼（僅宣告子類別與其各自的運算子/字面值白名單；具體 Stage 整合留給後續 changes）

## 6. Pipeline 介面與編排器（pipeline-foundation capability）

- [x] 6.1 於 `stages/base.py` 定義 PipelineStage interface（`name` 屬性與 `process()` 方法）；文件化 PipelineContext immutability and field semantics 與「停用 stage 必須原封不動回傳」契約
- [x] 6.2 於 `pipeline/orchestrator.py` 實作 PipelineOrchestrator drives stages in order；遵守 Orchestrator owns no business logic（不 import vad/transcription/alignment/post_processing/export/expression/io 任何模組）

## 7. CLI 與 smoke flow

- [x] 7.1 依「CLI entry point assembles dependencies; no service locator」決策，於 `cli.py` 實作入口：解析 argparse 引數、呼叫 `ConfigLoader.load()` 取得 `PipelineConfig`、用 `MediaHasher` 計算 hash、構建空 stage list 與 `PipelineOrchestrator`、執行後以 `ProjectFileWriter` 輸出 JSON
- [x] 7.2 對應「Five capabilities split aligned with module boundaries」決策，在 `tests/integration/test_pipeline_smoke.py` 撰寫端對端 smoke test：以 fixture YAML 與小型音訊樣本（test-samples/sample1）跑完 CLI 並斷言輸出 JSON 可被 `json.loads()`、含 media hash 與 config 快照
- [x] 7.3 補上單元測試：`tests/unit/config/test_loader.py`、`tests/unit/io/test_media_hasher.py`、`tests/unit/io/test_audio_reader.py`、`tests/unit/expression/test_base.py`，覆蓋每個 spec scenario（包含表格 Example 中列出的所有被拒絕表達式）
