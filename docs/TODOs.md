## 品質與工具

- [ ] 建立regression test的機制，來評估每次修改帶來的影響。目前 `test-samples/` 有我事先準備好的音頻檔，日後應該要使用這些音頻做轉錄，然後收集包含但不限制轉錄出來字幕的文字、信心水準、時間區間等資訊，最後評估轉錄品質是變差還是變好。
- [ ] 開發轉錄問題分析工具，要能夠視覺化的顯示音頻特徵（包含但不限制能量、頻率等資訊），且還要能檢視VAD分析的結果。最後還需要能播放影音檔，且要能夠顯示轉出出來的字幕。

## Split 邊界後續優化（japanese-aware-cue-split 的 follow-up）

來源：對 `test-samples/sample1` 的人工驗證（2026-05-08），確認 `japanese-aware-cue-split` 修正了文字切點，但留下以下問題待後續 change 處理。

- [x] **Split 後的時間戳對齊到 VAD 沉默區間**：由 `snap-split-timestamps-to-vad-silence`（archived 2026-05-08）解決，後續又被 `vad-driven-cue-split` 取代為主要決策訊號。
- [x] **擴充 `japanese_split_no_leading_finals` / `no_leading_particles` 預設清單**：原本要解決的四個案例（強/くて、持/つ、進/める、助/けて）由 `vad-driven-cue-split`（archived 2026-05-08）一併解決——文字切點現在從 VAD silence + aligned tokens 倒推，不再仰賴文字規則。`extend-japanese-split-leading-finals` change 永久 parked。
- [ ] **複合詞 / 漢字詞典保護**：目前 `japanese_split_no_split_units` 僅針對助動詞（まし、です、よう…），對「自動的」、「解決策」、「稼働した」這類複合詞無保護。要更乾淨需要小型字典或形態素分析，但這已超出 `japanese-aware-cue-split` 設計決策 4（Rule-based, no new dependency）的範圍——須開新 change 重新評估。

## Split 邊界後續優化（vad-driven-cue-split 的 follow-up）

來源：對 `test-samples/sample1` 的人工驗證（2026-05-08），確認 `vad-driven-cue-split` 解決了所有先前的 leading-final 案例，但 VAD-driven 路徑相信 silence midpoint + aligned tokens、跳過了 `JapaneseSplitBoundaryPolicy` 的把關，導致兩處新的 morpheme-internal 切點：

- [x] **VAD-driven 切點需經文法 sanity check**：分兩階段解決——
  - 配線（VAD-driven char_idx 通過 `JapaneseSplitBoundaryPolicy.is_valid` → 小半徑 snap → linear-fallback 三段判斷）由 `vad-grammar-sanity-gate`（archived 2026-05-09）落地。
  - 後續對 `test-samples/sample1` 的回測（2026-05-09）發現 sanity gate 在 cue 9/10 仍把「覚えてい / ます…」切出 leading-final，根因是 `JapaneseSplitBoundaryPolicy.adjust` 平手時偏好較小 index，正好把跨切點的 no-split unit「ます」推到下一句開頭。由 `straddle-aware-tie-break`（archived 2026-05-09）改為「candidate 被 no-split unit straddle 時，平手偏好較大 index」修正。
  - 配線生效後，未來 `is_valid` 加入更多規則（如下方複合詞保護），VAD-driven 路徑會自動受惠，無須再動 character_boundary。
