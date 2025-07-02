use anyhow::Result;
use std::fs;
use std::path::Path;

use ferrum_shared_models::FerrumDsl;

use super::utils::{copy_if_missing, ensure_dep};
use super::Plugin;

/// Stub plugin providing cron job support.
pub struct CronPlugin;

impl Plugin for CronPlugin {
    fn name(&self) -> &'static str {
        "cron"
    }

    fn on_init(&self) -> Result<()> {
        ensure_templates()?;
        ensure_env()?;
        ensure_dependencies()
    }

    fn on_compile(&self) -> Result<()> {
        ensure_templates()?;
        ensure_env()?;
        ensure_dependencies()
    }

    fn extend_dsl(&self, dsl: &mut FerrumDsl) -> Result<()> {
        if !dsl.app.features.contains(&"cron".to_string()) {
            dsl.app.features.push("cron".to_string());
        }
        if !dsl.jobs.iter().any(|j| j.name == "example_job") {
            dsl.jobs.push(ferrum_shared_models::DslJob {
                name: "example_job".to_string(),
                schedule: "0 0 * * *".to_string(),
                handler: "example_job".to_string(),
                policy: None,
            });
        }
        Ok(())
    }
}

fn ensure_env() -> Result<()> {
    let path = Path::new(".env");
    if !path.exists() {
        fs::write(path, "CRON_ENABLED=true\n")?;
    }
    Ok(())
}

fn ensure_templates() -> Result<()> {
    copy_if_missing(
        include_str!("../../../templates/batteries/jobs/example_job.rs.tera"),
        "backend/jobs/example_job.rs",
    )
}

fn ensure_dependencies() -> Result<()> {
    ensure_dep("tokio-cron-scheduler", "0.9")
}
