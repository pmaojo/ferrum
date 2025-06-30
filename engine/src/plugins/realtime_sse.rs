use anyhow::Result;
use std::fs;
use std::fs::OpenOptions;
use std::io::Write;
use std::path::Path;

use ferrum_shared_models::FerrumDsl;

use super::Plugin;

/// Plugin that scaffolds basic Server-Sent Events (SSE) support.
pub struct RealtimeSsePlugin;

impl Plugin for RealtimeSsePlugin {
    fn name(&self) -> &'static str {
        "realtime-sse"
    }

    fn on_init(&self) -> Result<()> {
        ensure_templates()?;
        ensure_dependencies()
    }

    fn on_compile(&self) -> Result<()> {
        ensure_templates()?;
        ensure_dependencies()
    }

    fn extend_dsl(&self, dsl: &mut FerrumDsl) -> Result<()> {
        if !dsl.app.features.contains(&"realtime-sse".to_string()) {
            dsl.app.features.push("realtime-sse".to_string());
        }
        Ok(())
    }
}

fn ensure_templates() -> Result<()> {
    copy_if_missing(
        include_str!("../../../templates/batteries/realtime_sse/backend/handlers/sse.rs.tera"),
        "backend/handlers/sse.rs",
    )?;
    copy_if_missing(
        include_str!("../../../templates/batteries/realtime_sse/backend/routes/sse.rs.tera"),
        "backend/routes/sse.rs",
    )?;
    copy_if_missing(
        include_str!("../../../templates/batteries/realtime_sse/frontend/hooks/useSse.ts.tera"),
        "frontend/src/hooks/useSse.ts",
    )?;
    Ok(())
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
    ensure_dep("axum-extra", "0.9")
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
