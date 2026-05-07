## Why

專案目前只有 `src/talking_parrot/__init__.py` 空檔案，但架構文件（`docs/architecture/`）已完整描述了 Whisper 影音轉錄 Pipeline 的五階段架構。後續所有 Stage（VAD、Transcription、Alignment、PostProcessing、Export）的實作都需要一組共同的基礎建設：資料模型、設定載入、編排器骨架、音訊讀取、安全表達式求值、CLI 入口。先把這些共用基礎建立起來，後續每個 Stage 才能各自以獨立的 change 並行展開，而不是把整個 Pipeline 塞進一個無法審閱的巨型 change。

## What Changes

- 新增 `pipeline-foundation` capability：定義 `PipelineStage` 抽象介面、`PipelineContext`、`PipelineOrchestrator` 編排語意、Stage 啟用/停用契約。
- 新增 `pipeline-config` capability：定義 YAML 設定檔格式、`PipelineConfig` 強型別模型、`ConfigLoader` 載入與驗證行為（含 `vad.max_speech_duration_ms` 與 `chunking.max_chunk_seconds` 不一致時的 WARNING 規則）。
- 新增 `pipeline-data-models` capability：定義所有跨 Stage 共享的純資料結構（`MediaInfo`、`VadSegment`、`Chunk`、`TranscriptionResult`、`TranscriptionMetrics`、`AlignmentResult`、`AlignedToken`、`Subtitle`、`ProjectFile`、`AlignmentStatus`、`AlignmentGranularity`、`GranularityPreference`）。
- 新增 `audio-io` capability：定義 `AudioReader` 介面（區間懶讀 + LRU 快取契約）、`MediaHasher`（SHA-256）、ffmpeg-based 預設實作的行為要求。
- 新增 `safe-expression` capability：定義 `SafeExpressionEvaluator` 抽象基底（白名單 AST walker、嚴禁 eval/exec、`ExpressionError` 例外契約），以及空 `FormulaEvaluator`、`ConditionEvaluator` 介面殼（具體運算子白名單由本 change 提供，但與 VAD/Transcription stage 整合留給後續 changes）。
- 新增 CLI 入口（`talking_parrot.cli`）：負責讀取環境變數、組裝依賴、呼叫 `PipelineOrchestrator`。本 change 中 CLI 僅執行「config 載入 + media hash + 空 stage 序列」的端對端 smoke flow，無實際轉錄行為。
- 新增 `pyproject.toml` 依賴宣告骨架（核心、`faster-whisper`、`mlx`、`dev` 四個群組）與 `LOG_LEVEL` / `MODEL_CACHE_DIR` / `TRANSCRIPTION_BACKEND` 環境變數約定。
- 新增 `ProjectFileWriter`：將 `ProjectFile` 序列化為 JSON。

## Non-Goals

- **不**實作任何 Stage 的具體邏輯（VAD、Chunking、Transcription、Alignment、PostProcessing、Export 全部留給後續 changes）。
- **不**整合任何 ML 模型載入（faster-whisper、mlx-whisper、wav2vec2、TEN VAD、Silero VAD 皆不在範圍內）。
- **不**實作 SRT / WebVTT 輸出（屬於 `export` capability，後續 change 處理）。
- **不**實作 `FormulaEvaluator` / `ConditionEvaluator` 的具體運算邏輯整合（基底白名單機制由本 change 建立，但 stage 端的呼叫流程在各 stage change 內完成）。
- **不**處理 regression test 機制（屬於 TODOs.md 第一項，獨立 change）與音訊分析工具（TODOs.md 第二項，獨立 change）。
- 拒絕的替代方案：將整個 Pipeline 塞進單一 change — 會超過 15 個 tasks 上限且無法審閱。

## Capabilities

### New Capabilities

- `pipeline-foundation`: `PipelineStage` 介面、`PipelineContext` 行為契約、`PipelineOrchestrator` 的 stage 序列驅動語意。
- `pipeline-config`: YAML 設定檔結構與 `ConfigLoader` 載入/驗證契約。
- `pipeline-data-models`: 所有跨 Stage 流動的純資料結構定義。
- `audio-io`: `AudioReader` 區間懶讀介面與 `MediaHasher` 雜湊契約。
- `safe-expression`: 表達式求值器的安全策略（白名單 AST walker、禁用 eval/exec、例外契約）。

### Modified Capabilities

(none)

## Impact

- Affected specs: 新增五個 capability 的 spec 檔。
- Affected code:
  - New:
    - src/talking_parrot/cli.py
    - src/talking_parrot/config/__init__.py
    - src/talking_parrot/config/loader.py
    - src/talking_parrot/config/models.py
    - src/talking_parrot/models/__init__.py
    - src/talking_parrot/models/context.py
    - src/talking_parrot/models/media.py
    - src/talking_parrot/models/vad.py
    - src/talking_parrot/models/chunk.py
    - src/talking_parrot/models/transcription.py
    - src/talking_parrot/models/subtitle.py
    - src/talking_parrot/models/project_file.py
    - src/talking_parrot/pipeline/__init__.py
    - src/talking_parrot/pipeline/orchestrator.py
    - src/talking_parrot/stages/__init__.py
    - src/talking_parrot/stages/base.py
    - src/talking_parrot/io/__init__.py
    - src/talking_parrot/io/media_hasher.py
    - src/talking_parrot/io/audio_reader.py
    - src/talking_parrot/io/audio_decoder.py
    - src/talking_parrot/io/project_writer.py
    - src/talking_parrot/expression/__init__.py
    - src/talking_parrot/expression/base.py
    - src/talking_parrot/expression/formula.py
    - src/talking_parrot/expression/condition.py
    - src/talking_parrot/logging_config.py
    - tests/unit/config/test_loader.py
    - tests/unit/io/test_media_hasher.py
    - tests/unit/io/test_audio_reader.py
    - tests/unit/expression/test_base.py
    - tests/integration/test_pipeline_smoke.py
  - Modified:
    - pyproject.toml
    - src/talking_parrot/__init__.py
  - Removed: (none)
