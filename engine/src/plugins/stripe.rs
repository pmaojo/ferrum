use anyhow::Result;
use std::fs;
use std::fs::OpenOptions;
use std::io::Write;
use std::path::Path;

use ferrum_shared_models::FerrumDsl;

use super::Plugin;

/// Stub plugin for Stripe payments.
pub struct StripePlugin;

impl Plugin for StripePlugin {
    fn name(&self) -> &'static str {
        "stripe"
    }

    fn on_init(&self) -> Result<()> {
        ensure_env()?;
        ensure_dependencies()
    }

    fn on_compile(&self) -> Result<()> {
        ensure_env()?;
        ensure_dependencies()
    }

    fn extend_dsl(&self, dsl: &mut FerrumDsl) -> Result<()> {
        if !dsl.app.features.contains(&"stripe".to_string()) {
            dsl.app.features.push("stripe".to_string());
        }
        Ok(())
    }
}

fn ensure_env() -> Result<()> {
    let path = Path::new(".env");
    if !path.exists() {
        fs::write(path, "STRIPE_SECRET=\nSTRIPE_WEBHOOK_SECRET=\n")?;
    }
    Ok(())
}

fn ensure_dependencies() -> Result<()> {
    ensure_dep("stripe", "0.23")
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
