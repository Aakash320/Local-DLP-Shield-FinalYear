# Local Shield DLP — Implementation Phases (v2, condensed)

Companion to `local-shield-dlp-design.md`. This is a build plan expanding that doc's Section 14.

**What's new in v2:** instead of watching Downloads/Desktop generically, there's now a **designated confidential-files folder** kept continuously indexed in a local **vector DB** (chunk → embed → store, synced on add/edit/delete). Uploads are checked for semantic similarity to that index, confirmed by a local LLM before anything is blocked. This adds Phases 3–5 (indexing, similarity search, LLM verification), mirroring the fast/expensive split the text pipeline already uses (Phase 1 → Phase 2).

**Portability principle:** Phase 0 sets up only the language runtime, dependencies, and general tooling — nothing that needs a model download or a heavy local service. All LLM/model environment setup (Ollama, chat model, embedding model) is deferred to the first phase that actually needs it: Phase 2 (chat model) and Phase 3 (embedding model). Phases 0–1 run on any machine with just Python, no GPU/RAM requirements and no Ollama.

**Time estimates** are focused-effort, not calendar time — expect 1.5–2× that alongside coursework (see Pacing Check at the end).

---

## Contents
0. Environment & Project Setup
1. Deterministic Detection Layer (Tier 0/1)
2. Local LLM Classifier (Tier 2)
3. Confidential File Store & Vector Indexing
4. Upload Interception: Similarity Search
5. Semantic Verification via Local LLM
6. Risk Fusion Engine
7. Policy Engine + Enforcement
8. Backend API + Audit Logging
9. Clipboard Monitor + Upload Channel Wiring
10. Browser Extension
11. Dashboard
12. Evaluation Harness & Benchmarking
13. Integration, Polish & Paper

---

## Phase 0 — Environment & Project Setup
*Est. 3–4 days*

**Goal:** prove the lightweight toolchain end-to-end before building real logic — with no LLM or model dependencies, so the repo stays portable and any teammate can be running in minutes.

**Key decisions:** pin the Python version; pick a vector DB (Chroma is the simplest default; FAISS/LanceDB as alternatives) — the DB library only, no embedding model; keep model names/endpoints in a config file (e.g. `config.yaml`) rather than hardcoding, so later phases can plug them in; mark LLM-dependent tests with a `pytest` marker (e.g. `@pytest.mark.llm`) so the default test run never needs Ollama.

**Build:**
1. Scaffold repo (`backend/`, `browser-extension/`, `dashboard/`, `docs/`), venv, `requirements.txt` with core deps only (fastapi, uvicorn, pytest, pydantic, watchdog, vector DB client, httpx/requests). No Ollama or embedding client yet.
2. `GET /health` → `{"status":"ok"}`.
3. Init an empty vector DB collection; insert/query a dummy vector **supplied manually** (fixed-size list of floats). Don't rely on the DB's built-in default embedding function — some (e.g. Chroma's) silently download a model on first use.
4. Basic tooling: `pytest` config + `llm` marker, linter/formatter, `.gitignore` (venv, vector DB data dir, SQLite files), config-file loader.
5. `README.md` with a **core setup** section (clone → venv → install → run tests → run server). Later phases append their own setup sections.
6. Commit design docs to `docs/`.

**Exit criteria:**
- [ ] Repo scaffolded, `/health` responds
- [ ] Vector DB dummy insert/query works (with manually supplied vectors, no model download)
- [ ] `pytest` runs clean with no Ollama installed
- [ ] Fresh clone + README core setup works on a second machine/teammate's laptop
- [ ] No LLM/embedding model or Ollama required anywhere in Phase 0

**Watch out for:** anything that quietly pulls a model (vector DB default embedders, NLP libraries) breaks the portability goal — check the install footprint. Keep model-related config keys present but empty/unused until Phases 2–3.

---

## Phase 1 — Deterministic Detection Layer (Tier 0 + Tier 1)
*Est. 2–3 weeks*

**Goal:** pure-Python, no server/LLM, string in → fired-patterns out. No I/O, fast, testable.

**Covers:** regex for AWS keys, emails, phone numbers, card shapes, DB connection strings, PEM headers; PAN structure; Aadhaar Verhoeff checksum (don't skip — plain 12-digit regex flags phone numbers/order IDs too); Luhn checksum for cards; Shannon entropy for unstructured secrets; a configurable "confidential" keyword list.

**Build:**
1. `detection/regex_detector.py`, `checksum_detector.py` (Luhn/Verhoeff/PAN), `entropy_detector.py`, `keyword_detector.py`.
2. Shared `Detection` result model: `{detector, category, confidence, span, tier}`.
3. `run_tier0(text)` and `run_tier1(text)` → `list[Detection]`.

**Integration:** feeds Phase 6's fusion engine for clipboard/paste events.

**Exit criteria:**
- [ ] Each detector tested against a hit and a clean miss
- [ ] Tier 0 isolated from Tier 1
- [ ] `run_tier0`/`run_tier1` are pure, millisecond-fast functions

**Watch out for:** tune entropy thresholds on your own data, not a borrowed number.

---

## Phase 2 — Local LLM Classifier (Tier 2)
*Est. 1.5–2 weeks*

**Goal:** set up the local LLM environment for the first time, then send ambiguous text to the local model and get back a structured verdict (not prose to regex apart). Build the Ollama wrapper generically — Phase 5 reuses it with a different prompt.

**Key decisions:** Ollama as the local LLM runtime; pick a chat model sized to your RAM/CPU (Qwen3-4B / Phi-4-mini / Llama-3.2-3B) and record it in config; use Ollama's `format` param for JSON-schema-constrained output; response schema `{"is_sensitive": bool, "category": str, "confidence": float, "reason": str}`; low/zero temperature; cap input length.

**Build:**
0. **LLM environment setup (moved from Phase 0):** install Ollama (skip if already installed for Phase 3), pull the chat model, confirm it responds via the API, add the chat model name/endpoint to config, and add an "LLM setup" section to the README (install Ollama, pull model, how to run `pytest -m llm`).
1. `detection/llm_client.py` — prompt-agnostic: `call_ollama(prompt, schema, timeout) -> dict`, with timeout + one retry.
2. `detection/llm_detector.py` — `classify(text) -> LLMVerdict`, built on top with the sensitivity prompt (narrow, example-anchored — small models are literal).
3. Timeout/failure path returns "needs review," never silently passes content through.

**Integration:** invoked only when Tier 1 is ambiguous (Phase 6 decides). Phase 5 imports `llm_client.py` directly with its own prompt, not `llm_detector.py`.

**Exit criteria:**
- [ ] Ollama installed and chat model pulled and responding via API
- [ ] LLM-dependent tests carry the `llm` marker; default `pytest` still passes without Ollama
- [ ] `classify()` always returns valid schema output
- [ ] Timeout path degrades safely
- [ ] Real P50/P95 latency measured
- [ ] `llm_client.py`/`llm_detector.py` cleanly separated

**Watch out for:** Ollama defaults to `127.0.0.1:11434` — don't expose it. Model pulls are multi-GB; document them in the README rather than assuming teammates have them.

---

## Phase 3 — Confidential File Store & Vector Indexing
*Est. 1.5–2 weeks · can be built in parallel with Phases 1–2 (depends on Phase 0, plus an Ollama install shared with Phase 2)*

**Goal:** a designated folder whose contents stay reflected, chunk-by-chunk, as embeddings in the vector DB — synced automatically on add/edit/delete. Pure indexing; no upload interception yet.

**Key decisions:** embedding model via Ollama (e.g. `nomic-embed-text` or similar — a separate pull from the chat model), recorded in config; chunking per file type (text/markdown by paragraph or token window w/ overlap; PDF/DOCX via extraction then same splitter; code by function/class, fallback to fixed windows); store per chunk: source path, chunk index, content hash, enough original text for Phase 5's LLM step; use `watchdog` for `on_created/modified/deleted/moved`; keep a SQLite `source_path -> chunk_ids` table so deletes are clean.

**Build:**
0. **Embedding environment setup (moved from Phase 0):** install Ollama if not already done in Phase 2, pull the embedding model, confirm the embeddings endpoint responds, add the model name to config, install any embedding client dependency, and extend the README's "LLM setup" section.
1. `indexing/chunker.py` (per file type → common `Chunk{text, source_path, chunk_index}`).
2. `indexing/embedder.py` — wraps embedding calls.
3. `indexing/vector_store.py` — `upsert`, `delete_by_source_path`, `similarity_search`.
4. `storage/chunk_index.py` — SQLite mapping table.
5. `indexing/full_reindex.py` — walks folder at startup, skips unchanged files via hash.
6. `indexing/watcher.py` — create → chunk/embed/upsert; modify → delete old chunks then re-index; delete → remove chunks + mapping row.
7. Config for watched folder(s), chunk size/overlap, embedding batch size.

**Integration:** feeds Phase 4's similarity search; `chunker.py`/`embedder.py` reused directly by Phase 4 on uploading files.

**Exit criteria:**
- [ ] Embedding model pulled and returning vectors of the expected dimension
- [ ] Startup re-index reflects current folder state, catches up on offline changes
- [ ] Add/modify/delete reflected in vector DB within seconds
- [ ] No orphaned vectors after delete (verify directly)
- [ ] Chunking works for text + PDF at minimum

**Watch out for:** the vector DB collection's dimension must match the embedding model's output — changing embedding models later means re-indexing everything. Debounce duplicate "modify" events from editor saves; batch embedding calls for large files.

---

## Phase 4 — Upload Interception: Similarity Search
*Est. 1–1.5 weeks*

**Goal:** cheap, LLM-free decision on whether an uploading file is even worth escalating — pure embedding similarity.

**Key decisions:** start with a permissive cosine-similarity threshold, tune later with Phase 12's eval data; decide per-chunk vs. pooled-embedding search; cap file size/type so huge files aren't chunked inline.

**Build:**
1. `matching/upload_scanner.py` — `find_candidates(file_bytes, filename) -> list[Candidate]`, reusing Phase 3's chunker/embedder.
2. Run `similarity_search()` per chunk, keep matches above threshold.
3. Group by matched source file, keep top score + matched chunk text/IDs.
4. Empty result → fast path, no LLM call.

**Integration:** produces `Candidate` list for Phase 5. No dependency on Phase 2's LLM code.

**Exit criteria:**
- [ ] Never calls Ollama (verify with Ollama stopped)
- [ ] Exact/near-duplicate content → high-similarity candidate
- [ ] Unrelated files → empty list
- [ ] Latency measured in isolation

**Watch out for:** threshold too low = candidates on every upload; too high = only literal copies match. Tune with real eval data, not eyeballing.

---

## Phase 5 — Semantic Verification via Local LLM
*Est. 1–1.5 weeks*

**Goal:** for Phase 4's candidates, ask the LLM whether the content is *semantically* the same/a derivative of the confidential reference — not just superficially similar (shared boilerplate/templates).

**Key decisions:** response schema `{"is_match": bool, "confidence": float, "reason": str}`; verify only the top candidate per matched source first, escalate only if ambiguous.

**Build:**
1. `matching/llm_verifier.py` — `verify_match(uploaded_content, candidate) -> MatchVerdict`, on Phase 2's `llm_client.py` with its own prompt.
2. Extend `upload_scanner.py` to call `verify_match()` for top candidate(s) after Phase 4.
3. Combined output: `VectorMatchResult{matched, matched_source_path, similarity_score, llm_verdict, llm_reason}` — feeds Phase 6.
4. Confirm empty-candidate fast path still short-circuits here (never calls the LLM with no candidates).

**Exit criteria:**
- [ ] A deliberately-constructed "similar but not confidential" case is correctly rejected (this justifies the phase's existence)
- [ ] `verify_match()` never runs with no candidates
- [ ] `VectorMatchResult` well-defined for Phase 6
- [ ] Separate latency numbers for "candidate found" vs. "no candidate" paths

**Watch out for:** don't skip the rejection test case — without it you can't show this phase adds anything beyond Phase 4's similarity score.

---

## Phase 6 — Risk Fusion Engine
*Est. 1 week*

**Goal:** one function turning whatever fired (Tier 0/1/2 for text, or `VectorMatchResult` for uploads) into a final score/band.

**Key decisions:** Tier 0 hit → Critical immediately (short-circuit); LLM-confirmed vector match → Critical too, same tier as Tier 0, carrying matched file + reason through for explainability; weighted-sum formula for the rest, tuned later.

**Build:**
1. `detection/fusion.py` — `fuse(tier0, tier1, tier2, vector_match=None) -> RiskResult`.
2. Tier 0 short-circuit first.
3. Vector-match short-circuit next (confirmed match → Critical, with source + reason attached).
4. "Is Tier 1 ambiguous enough to call Tier 2" check.
5. Weighted-sum formula for remaining cases; score→band thresholds in config.

**Exit criteria:**
- [ ] Tier 0 and confirmed vector matches always short-circuit to Critical (tested)
- [ ] Weights/thresholds centralized in config
- [ ] `fuse()` deterministic

**Watch out for:** don't let LLM confidence override what Tier 0/1 or a confirmed vector match already established.

---

## Phase 7 — Policy Engine + Enforcement
*Est. 1.5–2 weeks*

**Goal:** turn `RiskResult` into an actual decision with allowlist + thresholds, then enforce it.

**Key decisions:** YAML policy config; allowlist checked *before* thresholds; "block" means different things per source — clipboard can only be cleared after the fact, browser upload can be prevented before it lands (Phase 10); consider allowlist semantics for trusted internal tools receiving confidential files.

**Build:**
1. `policy/policies.yaml` — category → thresholds → enabled → exceptions, including `confidential_file_match`.
2. `policy/engine.py` — `decide(risk, source_app) -> Decision`.
3. Allowlist storage (app/domain, category, reason).
4. `allow()`/`warn()`/`block()` implementations, wired differently per source.

**Exit criteria:**
- [ ] Allowlist checked before thresholds
- [ ] Allow/Warn/Block all real, not stubs
- [ ] "Block" behavior documented per event source

**Watch out for:** test enforcement by hand — a passing unit test can still do nothing observable.

---

## Phase 8 — Backend API + Audit Logging
*Est. 1.5–2 weeks*

**Goal:** wrap Phases 1–7 into a running FastAPI service with persistence.

**Key decisions:** SQLModel over raw sqlite3; async FastAPI since LLM calls are I/O-bound; hash + redact (e.g. first/last 2 chars visible) before anything hits the DB.

**Build:**
1. `storage/db.py` — schema extended with `matched_source_path`, `similarity_score`, `llm_match_verdict`.
2. `storage/audit_log.py` — `record_event()`, hashes/truncates before writing.
3. `api/events.py` — `POST /events` (full pipeline for both text and file events), `GET /events`.
4. `api/policies.py` — CRUD for policy YAML.
5. `api/confidential_store.py` — status endpoints (indexed files/chunks, last sync, pending ops).

**Exit criteria:**
- [ ] `POST /events` runs the full pipeline for both event types
- [ ] `events` table never contains raw content (verify directly)
- [ ] `GET /events` returns real history
- [ ] Confidential-store status endpoint accurate

**Watch out for:** redaction happens *before* the row is written, not as cleanup after — applies to confidential-file text too, not just clipboard content.

---

## Phase 9 — Clipboard Monitor + Upload Channel Wiring
*Est. 1.5–2 weeks*

**Goal:** real input reaches the pipeline automatically via `POST /events`.

**Key decisions:** `pyperclip` polling to start (native hooks as a stretch); a few hundred ms polling interval; scope the upload channel realistically — a controlled "outbox" folder or a demo app's upload endpoint, not system-wide interception.

**Build:**
1. `monitoring/clipboard_monitor.py` — poll, dedupe against last-seen hash, capture foreground app, POST as text event.
2. `monitoring/upload_channel.py` — watches the outbox folder, POSTs file bytes as an upload event (replaces v1's generic file watcher entirely).
3. Config for locations/interval; dedup so resolved files/clipboard content aren't re-scanned.

**Exit criteria:**
- [ ] Clipboard detection doesn't busy-loop the CPU
- [ ] Upload channel triggers Phases 4–5 for every outbox file
- [ ] Both agents run for hours without crashing

**Watch out for:** pause monitoring during your own dev/testing to avoid noise; don't let leftover outbox test files re-trigger scans on restart.

---

## Phase 10 — Browser Extension
*Est. 2 weeks*

**Goal:** the most demoable piece — paste a fake secret or attach a confidential file copy, watch it get blocked live.

**Key decisions:** Manifest V3 — content scripts can't `fetch()` directly (CSP-bound); pattern is content script → `chrome.runtime.sendMessage()` → background service worker → fetch backend → send result back. `host_permissions` must list the backend origin. Decisions come back asynchronously (seconds when Tier 2/Phase 5 fire) — decide UX now: optimistic block-then-release vs. a visible "checking…" state.

**Build:**
1. `manifest.json` — MV3, content script matches, `host_permissions`.
2. `content_script.js` — `preventDefault()` on paste/file-change, send content via message.
3. `background.js` — receives message, `POST /events`, sends decision back.
4. Content script: Allow → re-insert + clear UI; Warn → banner; Block → stay blocked, show matched file + LLM reasoning for file matches.

**Exit criteria:**
- [ ] Loads cleanly in dev mode
- [ ] Blocked paste never reaches the input field
- [ ] Blocked file attachment never completes
- [ ] Benign pastes/uploads have no perceptible extra latency
- [ ] Async block/release UX actually implemented

**Watch out for:** budget slack here — MV3's content-script/service-worker split has real edge cases and tends to eat more time than estimated.

---

## Phase 11 — Dashboard
*Est. 2 weeks*

**Goal:** a local web UI showing status, event history, confidential-store status, policy config.

**Build:**
1. Vite + TanStack Query (`refetchInterval` for live-ish updates) against `GET /events`.
2. Status header — protection state, counts by risk band.
3. Event history table — timestamp, source, category, risk band, action, redacted preview, LLM reason, and for file matches: matched filename + similarity score.
4. Confidential-store status panel (indexed files/chunks, last sync, pending ops).
5. Policy view (read-only first).

**Exit criteria:**
- [ ] Live-ish event history, no manual refresh
- [ ] Nothing shown is raw sensitive content
- [ ] Confidential-store panel reflects real index state
- [ ] Runs entirely on localhost

**Watch out for:** don't over-polish the frontend — a clean functional table beats a half-finished chart for the demo.

---

## Phase 12 — Evaluation Harness & Benchmarking
*Est. 2–2.5 weeks*

**Goal:** turn the working tool into paper-ready results — for both the text pipeline and the file-matching pipeline, including whether Phase 5's LLM step actually improves on Phase 4 alone.

**Build:**
1. `tests/eval/labeled_dataset.csv` — synthetic `text, true_category, true_label` for text detection.
2. `tests/eval/labeled_file_pairs.csv` — synthetic (uploaded file, expected match or none) pairs, including deliberately near-duplicate-but-not-confidential pairs.
3. `tests/eval/run_eval.py` — text: Tier-1-only / LLM-only / full hybrid; files: similarity-only vs. similarity+LLM verification. Records predictions + latency.
4. Precision/recall/F1 per category per configuration, plus false-positive rate, for both pipelines.
5. Charts/tables for the results section.

**Exit criteria:**
- [ ] Both datasets exist, synthetic only
- [ ] P/R/F1 computed for all text configs
- [ ] P/R/F1 computed for Phase-4-only vs. Phase-4+5
- [ ] Latency recorded per configuration
- [ ] Results paper-ready

**Watch out for:** don't let the hybrid approach "win" by construction — make sure a real chunk of your file-pairs set is genuinely near-duplicate-but-not-confidential, or Phase 5 never gets a chance to prove its value.

---

## Phase 13 — Integration Testing, Polish & Paper
*Est. 3–4 weeks*

**Goal:** everything working together reliably, plus the write-up.

**Build:**
1. Fresh-venv, README-only end-to-end run, including Ollama install + model pulls and re-indexing the confidential folder from scratch — fix whatever breaks.
2. Paper: motivation → related work → architecture (vector pipeline as its own contribution) → design decisions (why similarity alone isn't enough) → results (Phase 12) → honest limitations (upload-channel scoping) → future work.
3. Demo script covering both a clipboard/text scenario and a file-upload-match scenario.

**Exit criteria:**
- [ ] Fresh-environment setup works from README alone
- [ ] Paper covers motivation → design → results → limitations for both pipelines
- [ ] Demo rehearsed live, covering both scenarios

**Watch out for:** frame limitations as deliberate scoping, not a weakness — evaluators notice the difference. Have someone else run your README cold.

---

## Phase Dependencies

```
Phase 0 (setup)
   ├──────────────────────┐
   ▼                       ▼
Phase 1 (detectors)   Phase 3 (vector indexing)
   ▼                       ▼
Phase 2 (LLM classifier)  Phase 4 (similarity search)
   │      │                     │
   │      └──────────┬──────────┘
   │                  ▼
   │            Phase 5 (LLM verification)
   │                  │
   └────────┬─────────┘
            ▼
     Phase 6 (risk fusion: text + file-match)
            ▼
     Phase 7 (policy + enforcement)
            ▼
     Phase 8 (API + audit log)
        │           │
        ▼           ▼
Phase 9 (clipboard + upload)   Phase 10 (browser extension)
        │           │
        └─────┬─────┘
              ▼
        Phase 11 (dashboard)
              ▼
        Phase 12 (evaluation)
              ▼
        Phase 13 (integration + paper)
```

Phase 3 only needs Phase 0 (plus Ollama, installed in whichever of Phase 2/3 you start first) — it can run in parallel with the text-detection track. Phase 0 and Phase 1 need no LLM environment at all. Phase 5 needs Phase 2's `llm_client.py` (not `llm_detector.py`) and Phase 4's candidates.

---

## Pacing Check

Total: roughly **22–28 weeks of focused effort** (~5.5–7 months). Splitting similarity search and LLM verification into two testable phases adds slight overhead but lets Phase 12 cleanly report whether the LLM step earns its place. With the 1.5–2× calendar factor for coursework, that's realistically **8–14 months** — fits a year-long project with less slack than a simpler plan. If you're running well outside this range by Phase 6/7, cut scope then — e.g. defer DOCX/code chunking in Phase 3 to a stretch goal, or merge Phases 4–5 back into one if the split isn't paying for itself.
