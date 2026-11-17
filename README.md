# Jira help docs pipeline

Python pipeline that turns the Atlassian Jira Cloud help docs export into a vector store, in four sections:

| Section | Module | Status |
|---|---|---|
| Loader | `pipeline/loader.py` | written |
| Chunker | `pipeline/chunker.py` | stub |
| Embed | `pipeline/embed.py` | stub |
| Upsert | `pipeline/upsert.py` | stub |

## Setup

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env   # then fill in the keys
```

Put the export at `data/atlassian_jira_cloud_help_docs_export_2025-03-07.json` (the `data/` folder is git-ignored).

## Run

```bash
python -m pipeline            # uses EXPORT_PATH or the default path
pytest
```

## What the loader handles

- `headings` stored as a JSON string → parsed to a list, `{#anchor}` suffixes removed
- `last_updated` in ISO, `DD/MM/YYYY` or `null` → `datetime.date`, falling back to the body's frontmatter; disagreements are logged
- YAML frontmatter stripped from `body_markdown` and kept in `Document.frontmatter`
- `doc_id` checked for uniqueness (URLs are not unique in this export), `record_count` checked against the docs found
