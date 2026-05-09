---
title: "ADR-0001: Browser-Based SPA over Local HTTP for Analysis GUI"
tags:
  - adr
  - gui
aliases:
  - adr-gui-spa
---

# ADR-0001: Browser-Based SPA over Local HTTP for Analysis GUI

## Status

Proposed

## Context

The Analysis GUI must visualise waveforms, VAD overlays, and subtitle tracks. Three implementation strategies were considered:

1. **Browser SPA over local HTTP** (vanilla JS + Python `http.server`)
2. **Desktop GUI framework** (Qt / PySide6, Tkinter, wxPython)
3. **Notebook-based** (Jupyter + matplotlib / ipywidgets)

The user has explicitly expressed satisfaction with the audio2subtitle GUI (which uses approach 1).

## Decision

Adopt approach 1: a single-page application served by a Python `http.server`-based local HTTP server, with a canvas-based timeline implemented in vanilla JavaScript.

## Rationale

| Criterion | Browser SPA | Desktop GUI | Notebook |
|---|---|---|---|
| No new Python GUI dep | Yes | No (PySide6 etc.) | No (jupyter) |
| Cross-platform | Yes | Partial | Yes |
| Native `<video>` + subtitle track | Yes (WebVTT) | Hard | No |
| Familiar to user | Yes (audio2subtitle) | No | No |
| Streaming audio/video via HTTP Range | Trivial | Complex | No |

Notebooks were rejected because they cannot provide a persistent, scrollable timeline without heavy ipywidgets complexity. Desktop GUI frameworks introduce large new dependencies and platform-specific packaging concerns.

## Consequences

- The GUI is accessed via `http://127.0.0.1:<port>` in any browser — no OS-level window management.
- Static files (HTML/CSS/JS) live in `src/talking_parrot/gui/static/`; no build step, no bundler.
- Audio/video streaming requires careful handling of HTTP `Range` headers (inherited directly from audio2subtitle's `http_server.py`).
- The GUI process must remain running for the browser to stay functional — acceptable for a developer tool.

## SOLID / 12-Factor Alignment

- **Factor VII**: GUI exposed via port binding, not injected by a web server.
- **Factor VI**: GUI HTTP server is stateless; `ProjectSnapshot` is loaded once at startup and never mutated.
- **SRP**: `api.py` contains only routing logic; `http_server.py` contains only HTTP lifecycle logic.
- **DIP**: `api.py` depends on `ProjectSnapshot` (abstraction), not on the filesystem directly.
