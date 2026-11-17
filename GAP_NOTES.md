# Gap notes

Data quality review of `atlassian_jira_cloud_help_docs_export_2025-03-07.json`, the raw export of the 40 Jira Cloud help pages, before the loader repairs anything. The full per-page listing is in [`inventory.txt`](inventory.txt).

Reproduce with:

```bash
python -m pipeline --inventory --out inventory.txt
```

## What counts as bad

Each rule lives in `RULES` in `pipeline/inventory.py`. A page is flagged when any rule fires.

| Field | Flag | Bad when |
|---|---|---|
| doc_id | DUPLICATE ID | the same doc_id is used by more than one page |
| title | MISSING TITLE | title is empty or null |
| title | TITLE MISMATCH | title differs from the frontmatter title or the `#` heading in the body |
| last_updated | MISSING DATE | last_updated is empty or null |
| last_updated | ODD DATE | last_updated is present but not ISO `YYYY-MM-DD` |
| last_updated | DATE CONFLICT | an ISO last_updated differs from the date in the body's frontmatter |
| headings | MISSING HEADING | headings is empty, null or unreadable |
| headings | DUPLICATE HEADING | the same section heading appears twice on one page |
| headings | HEADING ANCHOR | a heading carries anchor markup such as `{#browse-projects}` |
| headings | HEADING MISMATCH | the headings field differs from the `##` headings in the body |
| url | MISSING URL | url is empty or null |
| url | DUPLICATE URL | the url is shared with another page |
| url | URL MISMATCH | url differs from `source_url` in the frontmatter |
| body | EMPTY BODY | body_markdown is empty |
| body | NO FRONTMATTER | body_markdown does not start with a `---` frontmatter block |
| source_file | ODD FILENAME | source_file is not lowercase-kebab-case `.md` |
| word_count | WORD COUNT OFF | word_count is more than 15% away from the words actually in the body |

## Result

**40 pages, 11 flagged, 29 clean.** Ten of the seventeen rules found nothing: doc_id, title, url mismatch, body and word_count are clean on every page, and no page is missing its headings.

| Flag | Pages | Count |
|---|---|---|
| DATE CONFLICT | JCH-0008, JCH-0016, JCH-0024, JCH-0039 | 4 |
| ODD DATE | JCH-0004 (`07/02/2025`), JCH-0032 (`14/01/2025`) | 2 |
| DUPLICATE URL | JCH-0001 and JCH-0003 share one url | 2 |
| MISSING DATE | JCH-0006 | 1 |
| DUPLICATE HEADING | JCH-0002, "Before you begin" twice | 1 |
| HEADING ANCHOR | JCH-0003, `{#browse-projects}` | 1 |
| ODD FILENAME | JCH-0005, `Manage_Global_Permissions.md` | 1 |

### Zero counts: what came back clean

**Zero gaps: doc_id 0, title 0, body 0, word_count 0.** Inside fields that did have gaps, these rules also came back at 0: headings MISSING HEADING 0, HEADING MISMATCH 0; url MISSING URL 0, URL MISMATCH 0.

| Field | Rule | Count | Why it is clean |
|---|---|---|---|
| doc_id | DUPLICATE ID | 0 | 40 distinct ids, JCH-0001 to JCH-0040, one per page |
| title | MISSING TITLE | 0 | every page has a title |
| title | TITLE MISMATCH | 0 | on every page the title equals the frontmatter `title` and the `#` heading in the body |
| body | EMPTY BODY | 0 | every page has body text |
| body | NO FRONTMATTER | 0 | every body starts with a `---` frontmatter block |
| word_count | WORD COUNT OFF | 0 | every stored count is within 15% of the words in the body; the largest gap is JCH-0001, 298 stored vs 260 counted, 12.8%, as printed on the `word_count largest gap` line of `inventory.txt` |
| headings | MISSING HEADING | 0 | every headings field is present and decodes to a non-empty list |
| headings | HEADING MISMATCH | 0 | on all 40 pages the decoded list equals the `##` headings in the body, in order |
| url | MISSING URL | 0 | every page has a url |
| url | URL MISMATCH | 0 | every url equals `source_url` in the page's frontmatter |

No field is fully clean on last_updated or source_file: each of their rules flagged at least one page.

## Why each gap matters and how the pipeline handles it

**Dates feed check 3** (source file, heading and updated date on every vector), so they get the most care.

- **ODD DATE.** Read as day/month. Evidence: JCH-0032 stores `14/01/2025` in the field and `2025-01-14` in its frontmatter, and 14 cannot be a month. The loader converts both pages to ISO: JCH-0004 becomes `2025-02-07`, JCH-0032 becomes `2025-01-14`.
- **MISSING DATE.** JCH-0006 has no date in the field but `2025-02-05` in its frontmatter. The loader falls back to the frontmatter.
- **DATE CONFLICT.** On all four pages the field date is later than the frontmatter date. The loader keeps the field value, since it is the export's own metadata and the more recent of the two, and logs a warning for each page. **Open question:** confirm with the content owner named in the export which date is authoritative.

**Headings feed chunk labels and IDs.**

- **DUPLICATE HEADING.** Two sections of JCH-0002 have the same name, so an ID built from the heading name would collide and one chunk would overwrite the other. Chunk IDs therefore use doc_id plus position (`JCH-0002#3`), never the heading text.
- **HEADING ANCHOR.** The loader strips `{#...}` so the `heading` label reads cleanly.

**URLs.**

- **DUPLICATE URL.** JCH-0001 and JCH-0003 both point at the "Manage project permissions" page, so url cannot be a key: doc_id is. This also affects check 5 (right page in the top 3): both pages explain *Browse projects*, so the test set must say in advance which one counts as correct for that kind of question, or accept either.

**Cosmetic.**

- **ODD FILENAME.** JCH-0005's file name breaks the kebab-case convention. The pipeline does not rely on the naming, and `source_file` is carried as-is so that traceability points at the real file.

## Gaps outside the data

- **Embedding not executed.** The OpenAI key in `.env` is valid: the API answered `429 You have no credits remaining`, not `401`. The account has no credits, so `embed_test.py` could not print a measured dimension. `text-embedding-3-small` is documented at 1536 dimensions.
- **Pinecone index created.** `create_index.py` created `jira-cloud-help-docs` live: dimension 1536, metric cosine, status Ready, aws us-east-1. It used the documented dimension because OpenAI could not be called.
- **Chunker, embed and upsert** are still stubs, apart from `embed_texts`.
- **The export itself is not committed.** `data/` is git-ignored because it is third-party Atlassian content. Place the file at `data/atlassian_jira_cloud_help_docs_export_2025-03-07.json` to reproduce.
