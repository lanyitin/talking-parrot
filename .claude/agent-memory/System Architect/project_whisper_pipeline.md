---
name: Whisper Pipeline 專案背景
description: talking-parrot 是基於 Whisper 的影音轉錄 Pipeline，架構已設計完成
type: project
---

talking-parrot 是一個 Python 專案，將影音檔透過 VAD → Chunking → Transcription → HallucinationFilter → Alignment → PostProcessing 六階段 Pipeline 轉為字幕。

**Why:** 支援多平台（macOS 用 mlx-whisper，Windows/Linux 用 faster-whisper），並可透過 YAML 設定靈活控制各階段行為，包含 VAD formula 與 transcription condition 評估。

**How to apply:** 架構文件已建立於 `docs/architecture/`，後續討論功能設計時可直接參照這些文件。主要檔案：
- `docs/architecture/pipeline-overview.md` — 整體架構圖（6 stages）
- `docs/architecture/pipeline-data-models.md` — 資料模型（含 HallucinationFilterConfig、ExportConfig）
- `docs/architecture/pipeline-module-interfaces.md` — 各模組介面（含 SplitBoundaryPolicy、SplitTimePolicy、SubtitleExporterFactory）
- `docs/architecture/pipeline-directory-structure.md` — 目錄結構與套件依賴原則
- `docs/architecture/pipeline-post-processing-processors.md` — 後處理 Processor 家族（Dedup、Japanese、Policy 注入）
- `docs/architecture/ADR-0001-跨平台轉錄後端.md` — 平台後端選擇策略
- `docs/architecture/ADR-0002-condition-評估器.md` — condition 字串安全評估設計
- `docs/architecture/ADR-0003-對齊粒度與後處理策略.md` — 對齊粒度與後處理策略

test-samples/sample1/ 有測試用音訊（base.mp3 等），descriptor.yml 記錄預期轉錄文字（日文）。

TODOs.md 記錄兩個待辦：regression test 機制、轉錄問題分析工具（視覺化音頻特徵 + VAD 結果 + 字幕播放）。VAD-driven 切分後有兩個未解決的日文形態素邊界問題（詳見 TODOs.md）。
