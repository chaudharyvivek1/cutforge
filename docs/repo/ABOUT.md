# Paste this into the repository's About

GitHub's About panel is repository *metadata*, not a file: it cannot be set by a commit, and the App this repository is connected through has `contents: write` but not `administration: write`, so `gh repo edit` returns 403. Until the App is granted that permission, this file is the source of truth for what the About should say.

**Path:** repository page → **About** (top right, the gear icon) → paste the three fields below → Save.

---

## Description

```
Video engine: turns a sentence of intent into a frame-accurate cut. Timeline IR, exact rational time, MCP tool layer, 4K60 capacity and unit economics. Engine 3 of a multi-engine platform.
```

## Website

Leave blank, or use the specification once it is published anywhere:

```
```

## Topics

Paste one at a time — GitHub's topic field accepts a comma-separated list in some clients, but the UI adds them singly:

```
ai-video
video-editing
ffmpeg
mcp
video-engine
timeline-ir
system-architecture
technical-specification
otio
hdr
4k-video
design-document
render-pipeline
unit-economics
```

---

## Or do it in one command

If you have a personal access token with `administration: write`:

```bash
gh repo edit chaudharyvivek1/cutforge \
  --description "Video engine: turns a sentence of intent into a frame-accurate cut. Timeline IR, exact rational time, MCP tool layer, 4K60 capacity and unit economics. Engine 3 of a multi-engine platform." \
  --add-topic ai-video --add-topic video-editing --add-topic ffmpeg --add-topic mcp \
  --add-topic video-engine --add-topic timeline-ir --add-topic system-architecture \
  --add-topic technical-specification --add-topic otio --add-topic hdr \
  --add-topic 4k-video --add-topic design-document --add-topic render-pipeline \
  --add-topic unit-economics
```

## Or grant the App the permission once

GitHub → Settings → Applications → the installed App → **Configure** → Repository permissions → **Administration: Read and write** → Save. After that, `gh repo edit` works and so does any future engine's metadata, which is worth doing once for a platform that intends to add several.
