---
title: 架構文件索引
tags:
  - architecture
  - index
aliases:
  - 架構索引
---

# 架構文件索引

本目錄收錄 Whisper 影音轉錄 Pipeline 的所有架構設計文件。

## 主要文件

| 文件 | 說明 |
|------|------|
| [[pipeline-overview\|系統架構總覽]] | Pipeline 整體架構圖（6 stages）、各模組職責、SOLID / 12-Factor 對照 |
| [[pipeline-data-models\|Pipeline 資料模型]] | ER 圖與所有資料結構定義（VadSegment、TranscriptionResult、ProjectFile、HallucinationFilterConfig 等） |
| [[pipeline-module-interfaces\|模組介面設計]] | 每個模組的抽象介面與方法簽章，含 SplitBoundaryPolicy、SplitTimePolicy、SubtitleExporterFactory |
| [[pipeline-directory-structure\|目錄結構建議]] | Python 套件組織方式、依賴宣告原則、環境變數清單 |
| [[pipeline-post-processing-processors\|後處理 Processor 家族]] | 所有 SubtitleProcessor 實作（WORD/CHARACTER/Fallback/Dedup/Japanese）及 Policy 注入設計 |

## Architecture Decision Records (ADR)

| ADR | 決策主題 |
|-----|---------|
| [[ADR-0001-跨平台轉錄後端\|ADR-0001]] | 跨平台 Whisper 後端選擇策略（介面 + 工廠模式） |
| [[ADR-0002-condition-評估器\|ADR-0002]] | Transcription Condition 評估器設計（安全 AST 白名單） |
| [[ADR-0003-對齊粒度與後處理策略\|ADR-0003]] | 對齊粒度與後處理策略（AlignmentGranularity + 工廠模式） |
| [[ADR-0004-VAD-driven切分文法sanity-check整合\|ADR-0004]] | VAD-driven 切分 × 文法 sanity check 整合方針（VAD 主訊號 + 文法 gate） |