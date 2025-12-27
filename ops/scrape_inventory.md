# Scrape Inventory Summary

Found candidates for scraped data and related files in the repository:

- `crawler/seeds/tmp_test.yaml`: YAML seed file that appears to contain crawl configuration and seed URLs. It currently contains duplicate top-level keys (likely an edit/merge artifact).
- `.secrets/infinity-x-one-systems-sa.json`: Google service account JSON (sensitive). This was previously flagged and should be removed from git history if present in commits; keys must be rotated.

Observations:

- There is no `data/`, `outputs/`, `fixtures/`, or `exports/` directory in the repository root according to a workspace scan. The `docker-compose.yml` mounts a host `./data` directory into containers; scraped outputs might be stored there in deployments rather than in the repo.
- The project expects external services (Postgres, ChromaDB) for persistence — scraped results may be persisted to those systems rather than files inside the git repo.

Recommended next steps:

1. Inspect host `./data` (if present) and any backups for CSV/JSON/JSONL files and export them to a secured location.
2. If you want a repo-only inventory, permit me to recursively scan the backup directory that was created during cleanup (`mcp-backup-*`) for artifacts (I will only report file paths and summaries).
3. Remove `.secrets/infinity-x-one-systems-sa.json` from the repo and history (use `git-filter-repo`) if it exists in commits, and rotate the credentials immediately.
4. If the goal is to reconstitute scraped datasets into the pipeline, point the pipeline's data mounts to the recovered data folder and re-run ingestion.

If you want, I will now:

- Scan the backup directories for scraped data files and produce a per-file summary (type, size, sample lines).
- Or scan the host `./data` directory and report findings.

Update (backup scan):

- I scanned `mcp-backup-20251226-203308` and found JSON report files in `data/reports` and `results/uncategorized` and a small `tools/headless_test_results.json` file. The sampled JSON files appear to be cycle summary reports and in the samples the `seeds` arrays are empty.

Files summarized to: `ops/scrape_inventory_details.json`.

Next actions I can take now:

1. Recursively extract and sample larger data files from the backup (if any) and produce CSV/JSONL exports.
2. Inspect any mounted `./data` directory if you want live deployment data scanned.
3. Remove or redact the `.secrets` file from history and rotate the affected credentials (if this has not already been done).

