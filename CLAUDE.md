<!-- SPECTRA:START v1.0.2 -->

# Spectra Instructions

This project uses Spectra for Spec-Driven Development(SDD). Specs live in `docs/openspec/specs/`, change proposals in `docs/openspec/changes/`.

## Use `/spectra-*` skills when:

- A discussion needs structure before coding → `/spectra-discuss`
- User wants to plan, propose, or design a change → `/spectra-propose`
- Tasks are ready to implement → `/spectra-apply`
- There's an in-progress change to continue → `/spectra-ingest`
- User asks about specs or how something works → `/spectra-ask`
- Implementation is done → `/spectra-archive`
- Commit only files related to a specific change → `/spectra-commit`

## Workflow

discuss? → propose → apply ⇄ ingest → archive

- `discuss` is optional — skip if requirements are clear
- Requirements change mid-work? Plan mode → `ingest` → resume `apply`

## Parked Changes

Changes can be parked（暫存）— temporarily moved out of `openspec/changes/`. Parked changes won't appear in `spectra list` but can be found with `spectra list --parked`. To restore: `spectra unpark <name>`. The `/spectra-apply` and `/spectra-ingest` skills handle parked changes automatically.

<!-- SPECTRA:END -->

# 專案規範

## 文件存放

- 所有文件都必須放在 `docs/` 目錄內。
- `docs/` 是一個 Obsidian Vault，可以使用 `obsidian` 相關工具操作此目錄。

## 待辦事項追蹤

- @docs/TODOs.md 是目前的待辦事項清單，用來追蹤專案的事項與進度。
- 若發現任何待辦事項，都需要新增到此檔案。
- 使用者也會不定期新增項目。
