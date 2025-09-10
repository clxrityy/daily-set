ZAP Baseline reports

How to run

- Go to GitHub → Actions → “ZAP Baseline Scan”.
- Click “Run workflow”, set the target URL if needed (defaults to https://daily-set.fly.dev), then run.

Where to view results

- Summary tab (inline): The workflow publishes a Markdown summary with the key findings directly on the run’s Summary page.
- Artifacts: The workflow uploads an artifact named “zap-baseline-report” containing:
  - zap-report.html (full HTML report)
  - zap-report.json (machine-readable)
  - zap-report.md (Markdown summary)

How to download the artifacts (UI)

1. After the run completes, open the run page (Actions → ZAP Baseline Scan → latest run).
2. In the “Artifacts” section, click “zap-baseline-report”.
3. Download the zip and extract to access zap-report.html/json/md.

Optional: download via GitHub CLI

- Requires gh CLI authenticated to your repo.

```bash
# List latest runs for the workflow
gh run list --workflow "ZAP Baseline Scan" -L 5

# Download artifacts from the most recent run into ./zap-reports
RUN_ID=$(gh run list --workflow "ZAP Baseline Scan" -L 1 --json databaseId -q '.[0].databaseId')
gh run download "$RUN_ID" -n zap-baseline-report -D ./zap-reports
```

Notes

- The workflow is manual (workflow_dispatch). You can schedule it (cron) or trigger on PRs if desired.
- The target URL is configurable at dispatch time; ensure the app is reachable by the runner.
