# Cron Plugin

This plugin adds scheduled job support to Ferrum projects. It copies a sample job and ensures the required scheduler dependency.

## Usage

```bash
ferrum add cron
ferrum compile gen/app.yaml
```

The command generates `backend/jobs/example_job.rs` and injects the following DSL section:

```yaml
jobs:
  - name: example_job
    schedule: "0 0 * * *"
    handler: example_job
```

The plugin also writes `CRON_ENABLED=true` to `.env` if the file does not exist.
