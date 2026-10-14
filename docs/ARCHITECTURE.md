# Architecture decisions

## Evidence before derived output

Raw caption data is stored as JSON under `data/sources/<source-id>/`. Normalized timestamped chunks live in SQLite. Search and AI answers operate on chunks; summaries and plans are future derived artifacts, never replacements for the source.

## Local first, hybrid AI

SQLite and files are the source of truth. The app defaults to evidence-only answers. A configured OpenAI-compatible provider receives only retrieved chunks, which also allows an Ollama endpoint without changing the application boundary.

## Platform adapters

YouTube has a caption adapter. Instagram currently has an honest capture adapter only: it creates a durable source record without claiming media extraction. Each platform remains isolated so a failure or policy change does not corrupt the library.

## REA usage

REA is not an app dependency. Use it only for authorized, narrow runtime investigations and document observations separately from inferences. Prefer ordinary source review for open-source references.
