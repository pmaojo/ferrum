use anyhow::Result;

use ferrum_shared_models::FerrumDsl;

use super::Plugin;
use super::utils::{copy_if_missing, ensure_env_var}; // Updated import

/// Plugin that scaffolds password-based authentication support.
pub struct AuthPasswordPlugin;

impl Plugin for AuthPasswordPlugin {
    fn name(&self) -> &'static str {
        "auth-password"
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
        if !dsl.app.features.contains(&"auth".to_string()) {
            dsl.app.features.push("auth".to_string());
        }

        if dsl.app.auth.is_none() {
            dsl.app.auth = Some(ferrum_shared_models::DslAuth {
                user_entity: "User".to_string(),
                methods: vec!["password".to_string()],
                on_auth_failed_redirect_to: Some("/login".to_string()),
            });
        }

        Ok(())
    }
}

fn ensure_env() -> Result<()> {
    ensure_env_var("JWT_SECRET", "change_me")?;
    ensure_env_var("AUTH_REDIRECT", "/login")?;
    ensure_env_var("REDIS_URL", "redis://localhost:6379")?;
    Ok(())
}

fn ensure_templates() -> Result<()> {
    copy_if_missing(
        include_str!("../../../templates/batteries/auth/backend/handlers/auth.rs.tera"),
        "backend/handlers/auth.rs",
    )?;
    copy_if_missing(
        include_str!("../../../templates/batteries/auth/backend/routes/auth.rs.tera"),
        "backend/routes/auth.rs",
    )?;
    copy_if_missing(
        include_str!("../../../templates/batteries/auth/frontend/hooks/useLogin.ts.tera"),
        "frontend/src/hooks/useLogin.ts",
    )?;
    copy_if_missing(
        include_str!("../../../templates/batteries/auth/frontend/components/LoginForm.tsx.tera"),
        "frontend/src/components/LoginForm.tsx",
    )?;
    copy_if_missing(
        include_str!("../../../templates/batteries/auth/backend/sessions.rs.tera"),
        "backend/sessions.rs",
    )?;
    Ok(())
}

fn ensure_dependencies() -> Result<()> {
    ensure_dep("redis", "0.23")
}

fn ensure_dep(dep: &str, version: &str) -> Result<()> {
    use std::fs::{self, OpenOptions};
    use std::io::Write;
    use std::path::Path;
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
