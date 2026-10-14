# Knowledge Forge

Knowledge Forge is a local-first, evidence-grounded library for useful YouTube and Instagram sources. It saves the original source record and timestamped transcript evidence locally, then returns citations with every AI answer.

## What works now

- Paste a public YouTube or Instagram URL into one inbox.
- Normalize URLs and prevent duplicate saves.
- Retrieve publicly available YouTube captions with `youtube-transcript-api`.
- Preserve the caption response locally and index timestamped transcript chunks with SQLite FTS5.
- Search exact transcript evidence and export it as portable Markdown.
- Ask an OpenAI-compatible model questions using only retrieved local evidence; use evidence-only mode until an API key is configured.
- Create collections through the API.

Instagram links are stored honestly as sources. Automated Reel transcription or saved-post synchronization is intentionally not implemented: it needs a separate, permission-aware feasibility decision.

## Run locally

```bash
python3 -m venv .venv
.venv/bin/python -m pip install -e '.[dev]'
cp .env.example .env
set -a; source .env; set +a
.venv/bin/uvicorn knowledge_forge.app:app --reload
```

Open [http://127.0.0.1:8000](http://127.0.0.1:8000). Local data is written to `data/`, which Git ignores.

## API

- `POST /api/sources` — save a URL.
- `POST /api/sources/{id}/ingest` — attempt caption ingestion for YouTube.
- `GET /api/sources/{id}` — inspect one source.
- `GET /api/search?q=...` — retrieve timestamped evidence.
- `POST /api/chat` — ask a grounded question.
- `POST /api/collections` — create a project/topic collection.

## Architecture

```text
URL inbox → canonical source record → platform adapter → raw transcript on disk
                                           ↓
                                  SQLite metadata + FTS5 chunks
                                           ↓
                         retrieval → optional model → cited answer
```

The current retrieval path is exact full-text search. LanceDB is included as the planned vector-store dependency; semantic embeddings are deliberately the next increment, after the evaluation corpus proves the lexical evidence path.

## Privacy and portfolio boundaries

The repository must contain only original code, synthetic/public fixtures, and documentation. Never commit `data/`, `.env`, account cookies, private transcripts, downloaded protected media, or provider keys. Read [PRIVACY.md](PRIVACY.md) before adding connectors.

## Verification

```bash
.venv/bin/python -m pytest
.venv/bin/ruff check .
```

## Next milestones

1. Add a local/vector embedding adapter and hybrid ranker backed by LanceDB.
2. Create the evaluation corpus and cited-answer benchmark.
3. Add user-permitted media upload plus local Whisper fallback.
4. Run the Instagram saved-content feasibility study before considering sync.
