## 品質與工具

- [ ] 建立regression test的機制，來評估每次修改帶來的影響。目前 `test-samples/` 有我事先準備好的音頻檔，日後應該要使用這些音頻做轉錄，然後收集包含但不限制轉錄出來字幕的文字、信心水準、時間區間等資訊，最後評估轉錄品質是變差還是變好。
- [ ] 開發轉錄問題分析工具，要能夠視覺化的顯示音頻特徵（包含但不限制能量、頻率等資訊），且還要能檢視VAD分析的結果。最後還需要能播放影音檔，且要能夠顯示轉出出來的字幕。
- [ ] 設計一個MCP Server，讓AI Agent能夠一同協助分析問題。
## Split 邊界後續優化（japanese-aware-cue-split 的 follow-up）

來源：對 `test-samples/sample1` 的人工驗證（2026-05-08），確認 `japanese-aware-cue-split` 修正了文字切點，但留下以下問題待後續 change 處理。
- [ ] **複合詞 / 漢字詞典保護**：目前 `japanese_split_no_split_units` 僅針對助動詞（まし、です、よう…），對「自動的」、「解決策」、「稼働した」這類複合詞無保護。要更乾淨需要小型字典或形態素分析，但這已超出 `japanese-aware-cue-split` 設計決策 4（Rule-based, no new dependency）的範圍——須開新 change 重新評估。