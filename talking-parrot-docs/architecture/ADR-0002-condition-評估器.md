---
title: "ADR-0002: Transcription Condition 評估器設計"
tags:
  - adr
  - architecture
  - transcription
  - condition
aliases:
  - ADR-0002
---

# ADR-0002: Transcription Condition 評估器設計

## Status

Accepted

## Context

YAML 設定中的 `transcribing` 欄位允許使用者以字串表達式描述「何時啟用某個模型」：

```yaml
transcribing:
- model: medium
  condition: true
- model: large-v3
  condition: avg_logprob < -1.0 && repetition_ratio > 0.4 && no_speech_prob < 0.3
```

此設計帶來幾個技術決策點：

1. **如何安全地對字串表達式求值**，同時允許引用 `TranscriptionMetrics` 的欄位名稱作為變數
2. **condition 的評估時機**：第一個 step（`condition: true`）應無條件執行；後續 step 的 condition 需要前一次轉錄的 metrics 才能評估
3. **表達式語法的邊界**：允許哪些運算子、禁止哪些（避免任意程式碼執行）

## Decision

### 評估器介面

定義 `ConditionEvaluator` 介面（見 [[pipeline-module-interfaces#1.5 ConditionEvaluator]]），接收 `condition` 字串與 `TranscriptionMetrics` 物件，回傳 `bool`。

### 語法支援範圍

支援以下元素的子集，其餘一律拒絕：

| 支援 | 範例 |
|------|------|
| 數值字面值 | `0.4`, `-1.0`, `0.3` |
| 識別字（metrics 欄位名稱） | `avg_logprob`, `compression_ratio`, `no_speech_prob`, `repetition_ratio` |
| 比較運算子 | `<`, `>`, `<=`, `>=`, `==`, `!=` |
| 邏輯運算子 | `&&`（AND）, `\|\|`（OR）, `!`（NOT） |
| 括號 | `(`, `)` |
| 特殊常數 | `true`, `false` |

禁止：函式呼叫、字串、import、賦值、任何形式的陳述式（statement）。

### 實作策略

使用**手寫遞降解析器（Recursive Descent Parser）**或以 Python `ast` 模組解析後白名單（whitelist）走訪 AST 節點：

1. 解析為 AST
2. 走訪 AST，若遇到任何非白名單的節點型別（例如 `ast.Call`, `ast.Import`），立即拋出 `ConditionError`
3. 以 `TranscriptionMetrics` 的欄位值填入識別字，對 AST 求值

**嚴禁使用 `eval()` 或 `exec()`**，即使加上 `locals` 限制也不安全，因為 Python 的 `__builtins__` 保護機制存在已知繞過方式。

### 執行時機（在 TranscriptionStage 內的流程）

```
對每個 Chunk：

1. 初始化一個空的 TranscriptionMetrics（所有欄位為 None）
2. 遍歷 TranscribingStep 清單（按設定順序）：
   a. 將 condition 字串對「目前的 metrics」求值
   b. 若結果為 True：
      - 呼叫 backend.transcribe() 以此 step 的 model
      - 用新的轉錄結果更新 metrics
      - 繼續檢查下一個 step
   c. 若結果為 False：
      - 跳過此 step
3. 使用最後一次成功轉錄的結果作為此 Chunk 的 TranscriptionResult
```

> **注意**：若第一個 step 的 condition 不是 `true`，而是依賴 metrics 的表達式，則在第一次執行時 metrics 為空，會拋出 `ConditionError`（因識別字未定義）。這是故意的設計：提示使用者第一個 step 應使用 `condition: true`。

## Rationale

**為何不用 Python `eval()`？**
安全性風險無法完全消除。即便加上 `{"__builtins__": {}}` 也存在已知的繞過方式，且行為在不同 Python 版本間可能不一致。

**為何不用第三方表達式引擎（例如 `simpleeval`）？**
可行，但引入額外依賴。若選用，需在 `ConditionEvaluator` 的具體實作中封裝，不改變介面設計。日後可透過 OCP 替換實作而不影響 Stage。

**為何 condition 要對「前一次的 metrics」求值，而非在所有轉錄完成後評估？**
這允許「級聯升級」的使用模式：先以快速模型轉錄，若品質不佳則立即以更好的模型重轉同一個 Chunk，避免對品質良好的 Chunk 浪費計算資源。

**級聯升級的收斂保證**

級聯升級依靠使用者撰寫合理的 condition 才能達到「品質不夠才升級」的目的。系統層面提供以下保證與限制：

1. **重試次數隱式上限**：`TranscribingStep` 清單長度本身即為最大重試次數。每個 step 至多執行一次（依序求值，不回頭），因此即使所有 condition 皆為 True，最差情況也只重轉 N 次（N = step 數）。**不需要額外的 `max_retries` 欄位**——清單長度即上限。

2. **建議寫法（單調收斂）**：使用者撰寫多 step condition 時，應確保「後一個 step 的 condition 比前一個更嚴格」。例如：
   ```yaml
   transcribing:
   - model: medium       # 永遠跑
     condition: true
   - model: large-v3     # 只在品質明顯不佳時才升級
     condition: avg_logprob < -1.0 && repetition_ratio > 0.4
   - model: large-v3-quantized   # 反例：若條件比上一個更寬鬆，會浪費算力
     condition: avg_logprob < -0.5
   ```
   反例中第三個 step 的閾值（−0.5）比第二個（−1.0）寬鬆，幾乎必然成立，會無謂多跑一次大模型。系統不阻止此寫法，但文件層面警告使用者注意。

3. **不做動態保險**：系統**不會**在「升級後 metrics 變差」時自動回退。這是有意識的取捨——回退邏輯會讓行為對使用者不透明，且難以在 condition 中表達「我預期升級後會變好」的意圖。若使用者希望此行為，應在 condition 中加入 sanity check（例如比較前後值，但目前語法不支援，需未來擴充）。

## Consequences

**正面**
- condition 語法簡單直觀，與 YAML 設定自然整合
- 安全性由 whitelist AST 走訪保證，不依賴 sandbox 機制
- `ConditionEvaluator` 可獨立單元測試，不需要真實音訊

**需注意的取捨**
- 不支援複雜的函式表達式（例如 `abs(avg_logprob) > 0.5`），若未來有需求，需擴充 whitelist 並更新此 ADR
- `repetition_ratio` 並非 Whisper 原生輸出，需在 Backend 層計算並填入 `RawTranscriptionOutput`；各 Backend 的計算方式應一致，否則跨平台的 condition 行為會有差異

## SOLID / 12-Factor Alignment

| 原則 | 如何滿足 |
|------|---------|
| SRP | `ConditionEvaluator` 只負責表達式求值，不知道轉錄細節 |
| OCP | 未來可替換 `ConditionEvaluator` 實作（例如換用第三方引擎）而不修改 Stage |
| ISP | `ConditionEvaluator` 只暴露一個 `evaluate()` 方法 |
| DIP | `TranscriptionStage` 依賴 `ConditionEvaluator` 介面，不依賴具體解析實作 |
| Factor III | condition 字串來自 YAML 設定，不硬編碼在程式碼中 |