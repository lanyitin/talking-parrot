---
name: User GUI preference — audio2subtitle style
description: User likes the browser-based SPA GUI from audio2subtitle; adopt that architecture for talking-parrot GUI
type: user
---

User explicitly stated: "audio2subtitle 的 GUI 介面我很喜歡" (I really like the audio2subtitle GUI interface).

audio2subtitle GUI is a browser SPA served by Python `http.server`, with a canvas-based timeline (vanilla JS), `/api/*` JSON endpoints, and `<video>` element for playback with WebVTT subtitle injection.

**How to apply:** When designing or implementing any visual tool for talking-parrot, default to this same browser-SPA-over-local-HTTP pattern. Do not propose Qt, Tkinter, or Jupyter alternatives unless the user asks.
