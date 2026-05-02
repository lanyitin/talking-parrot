## Pipeline 實作（依賴 bootstrap-pipeline-foundation）

- [x] `implement-vad-stage`：實作 `VADStage`，整合 `TenVADBackend`、`SileroVADBackend`，並以 `FormulaEvaluator` 計算 composite score，輸出 `VadSegment` 清單。
- [X] `implement-chunking-stage`：實作 `ChunkingStage`，貪婪合併 VadSegment 至 max_chunk_seconds，含 silence_pad 與超長硬切兜底邏輯。
- [X] `implement-transcription-stage`：實作 `TranscriptionStage`，整合 `FasterWhisperBackend`（Windows/Linux）與 `MLXWhisperBackend`（macOS），並以 `ConditionEvaluator` 實現級聯升級邏輯。
- [X] `implement-alignment-stage`：實作 `AlignmentStage`，整合 `EnglishAlignmentBackend`（word-level wav2vec2）與 `JapaneseAlignmentBackend`（character-level），並實作 `AlignmentBackendFactory` 語言路由。
- [X] `implement-post-processing-stage`：實作 `PostProcessingStage` 與六個 `SubtitleProcessor`（WordBoundaryMerge/Split、CharacterBoundaryMerge/Split、TimeBasedMerge/Split）及 `GranularityAwareProcessorFactory`。
- [ ] `implement-subtitle-export`：實作 `SRTExporter` 與 `WebVTTExporter`，完成完整端對端 Pipeline 輸出流程。

## 品質與工具

- [ ] 建立regression test的機制，來評估每次修改帶來的影響。目前 `test-samples/` 有我事先準備好的音頻檔，日後應該要使用這些音頻做轉錄，然後收集包含但不限制轉錄出來字幕的文字、信心水準、時間區間等資訊，最後評估轉錄品質是變差還是變好。
- [ ] 開發轉錄問題分析工具，要能夠視覺化的顯示音頻特徵（包含但不限制能量、頻率等資訊），且還要能檢視VAD分析的結果。最後還需要能播放影音檔，且要能夠顯示轉出出來的字幕。
