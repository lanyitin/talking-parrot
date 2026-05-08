## Pipeline 實作（依賴 bootstrap-pipeline-foundation）

- [x] `implement-vad-stage`：實作 `VADStage`，整合 `TenVADBackend`、`SileroVADBackend`，並以 `FormulaEvaluator` 計算 composite score，輸出 `VadSegment` 清單。
- [X] `implement-chunking-stage`：實作 `ChunkingStage`，貪婪合併 VadSegment 至 max_chunk_seconds，含 silence_pad 與超長硬切兜底邏輯。
- [X] `implement-transcription-stage`：實作 `TranscriptionStage`，整合 `FasterWhisperBackend`（Windows/Linux）與 `MLXWhisperBackend`（macOS），並以 `ConditionEvaluator` 實現級聯升級邏輯。
- [X] `implement-alignment-stage`：實作 `AlignmentStage`，整合 `EnglishAlignmentBackend`（word-level wav2vec2）與 `JapaneseAlignmentBackend`（character-level），並實作 `AlignmentBackendFactory` 語言路由。
- [X] `implement-post-processing-stage`：實作 `PostProcessingStage` 與六個 `SubtitleProcessor`（WordBoundaryMerge/Split、CharacterBoundaryMerge/Split、TimeBasedMerge/Split）及 `GranularityAwareProcessorFactory`。
- [X] `implement-subtitle-export`：實作 `SRTExporter` 與 `WebVTTExporter`，完成完整端對端 Pipeline 輸出流程。

## 品質與工具

- [ ] 建立regression test的機制，來評估每次修改帶來的影響。目前 `test-samples/` 有我事先準備好的音頻檔，日後應該要使用這些音頻做轉錄，然後收集包含但不限制轉錄出來字幕的文字、信心水準、時間區間等資訊，最後評估轉錄品質是變差還是變好。
- [ ] 開發轉錄問題分析工具，要能夠視覺化的顯示音頻特徵（包含但不限制能量、頻率等資訊），且還要能檢視VAD分析的結果。最後還需要能播放影音檔，且要能夠顯示轉出出來的字幕。

## Split 邊界後續優化（japanese-aware-cue-split 的 follow-up）

來源：對 `test-samples/sample1` 的人工驗證（2026-05-08），確認 `japanese-aware-cue-split` 修正了文字切點，但留下以下問題待後續 change 處理。

- [ ] **Split 後的時間戳對齊到 VAD 沉默區間**：`CharacterBoundarySplitProcessor` 與 `TimeBasedSplitProcessor` 目前固定按 `(i+1)/n × duration` 線性平均切分時間。結果是文字往語法邊界 snap 後，時間戳仍停在中央，視覺上會出現「講者話講到一半字幕就換頁」的錯位。建議：split processor 在決定時間切點時，於候選時間附近的小窗內找最近的 VAD silence 對齊。
- [ ] **擴充 `japanese_split_no_leading_finals` / `no_leading_particles` 預設清單**：目前 leading-final 只覆蓋 `た, だ, る, い`，仍有以下案例逃過規則：
  - 「気持ちが強 / くて」（`く` 不在清單）
  - 「興味を持 / つように」（`つ` 不在清單）
  - 「進 / める方が」（`め` 不在清單）
  - 「先輩に助 / けてもらった」（`け` 不在清單）

  可考慮：(a) 擴充清單；(b) 加上「禁止把 hira-ending 的動詞活用尾切離 kanji 詞幹」這類更通用的規則。
- [ ] **複合詞 / 漢字詞典保護**：目前 `japanese_split_no_split_units` 僅針對助動詞（まし、です、よう…），對「自動的」、「解決策」、「稼働した」這類複合詞無保護。要更乾淨需要小型字典或形態素分析，但這已超出 `japanese-aware-cue-split` 設計決策 4（Rule-based, no new dependency）的範圍——須開新 change 重新評估。
