# Local Shield DLP

A local-first data loss prevention (DLP) system. It detects sensitive text and confidential files before they leave your machine, using deterministic detectors, a local LLM, and vector similarity search. Everything runs on localhost; nothing sensitive leaves the device.

> **Status:** Phase 0 (environment setup) complete. See `docs/` for the design, phases, and architecture.

## Prerequisites

- Python 3.12 (3.11 also works)
- Git
- No GPU, no Ollama, and no model downloads are needed until Phase 2.

## Core setup

### Windows (PowerShell)

```powershell
git clone https://github.com/Aakash320/Local-DLP-Shield-FinalYear.git
cd local-shield-dlp

py -3.12 -m venv .venv
.venv\Scripts\Activate.ps1
```

If activation fails with "running scripts is disabled", run this once and retry:

```powershell
Set-ExecutionPolicy -Scope CurrentUser -ExecutionPolicy RemoteSigned
```

Then:

```powershell
python -m pip install --upgrade pip
pip install -r requirements.txt
```

### macOS / Linux

```bash
git clone https://github.com/Aakash320/Local-DLP-Shield-FinalYear.git
cd local-shield-dlp

python3 -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
```

## Run the tests

```bash
pytest
```

Tests that need a local model are marked `llm` and are skipped by default, so this passes without Ollama installed. To run them later (after LLM setup): `pytest -m llm`.

## Run the server

```bash
uvicorn backend.api.main:app --reload
```

Check that it's up:

```powershell
curl.exe http://127.0.0.1:8000/health
```

Expected response: `{"status":"ok"}`

## Project structure

```
backend/          API, detection, indexing, matching, policy, storage, monitoring
browser-extension/  Browser extension (Phase 10)
dashboard/        Local dashboard UI (Phase 11)
tests/            Unit tests and evaluation data
docs/             Design doc, phases plan, architecture
config.yaml       Central configuration (model settings stay empty until Phases 2-3)
```

## Configuration

All settings live in `config.yaml`. Model names and the Ollama URL are intentionally empty for now.

## LLM setup (Phases 2-3)

_Not required yet._ This section will cover installing Ollama, pulling the chat model (Phase 2), and pulling the embedding model (Phase 3).

## Docs

- `docs/local-shield-dlp-design.md`: design and rationale
- `docs/local-shield-dlp-phases-latest.md`: phased build plan
- `docs/local-shield-dlp-architecture.md`: progressive architecture