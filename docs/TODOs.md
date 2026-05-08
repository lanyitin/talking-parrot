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

- [ ] **VAD-driven 切點需經文法 sanity check**：當 VAD 找到的 silence 落在助動詞或動詞活用尾內部時，aligned tokens 會老實地把 char_idx 對到 morpheme 中央。實際輸出有兩處：
  - cue 7/8：「専攻しておりまし / た」（まし／た 切開）
  - cue 9/10：「覚えていま / す」（い ま／す 切開）

  建議方向：VAD-driven 路徑算出 char_idx 後，再丟給 `JapaneseSplitBoundaryPolicy._is_valid`；若 invalid 則在小範圍內找最近 valid 位置，或退回完整文法 fallback。VAD 仍是主要訊號，文法只當 sanity gate。
