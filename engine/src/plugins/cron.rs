use anyhow::Result;
use std::fs;
use std::fs::OpenOptions;
use std::io::Write;
use std::path::Path;

use ferrum_shared_models::FerrumDsl;

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

fn copy_if_missing<P: AsRef<Path>>(contents: &str, dest: P) -> Result<()> {
    let dest = dest.as_ref();
    if dest.exists() {
        return Ok(());
    }
    if let Some(parent) = dest.parent() {
        fs::create_dir_all(parent)?;
    }
    fs::write(dest, contents)?;
    Ok(())
}

fn ensure_dependencies() -> Result<()> {
    ensure_dep("tokio-cron-scheduler", "0.9")
}

fn ensure_dep(dep: &str, version: &str) -> Result<()> {
    let path = Path::new("backend/Cargo.toml");
    if !path.exists() {
        return Ok(());
    }
    let contents = fs::read_to_string(path)?;
    if !contents.contains(dep) {
        let mut f = OpenOptions::new().append(true).open(path)?;
        writeln!(f, "{dep} = \"{version}\"")?;
    }
    Ok(())
}
