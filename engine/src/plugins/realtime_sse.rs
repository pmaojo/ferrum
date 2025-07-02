use anyhow::Result;

use ferrum_shared_models::FerrumDsl;

use super::utils::{copy_if_missing, ensure_dep};
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

fn ensure_dependencies() -> Result<()> {
    ensure_dep("axum-extra", "0.9")
}
