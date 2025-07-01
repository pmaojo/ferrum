use anyhow::Result;

use ferrum_shared_models::FerrumDsl;

use super::Plugin;
use super::utils::{copy_if_missing, ensure_env_var}; // Updated import

/// Plugin that scaffolds OAuth authentication with Google and GitHub.
pub struct AuthOAuthPlugin;

impl Plugin for AuthOAuthPlugin {
    fn name(&self) -> &'static str {
        "auth-oauth"
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
        if !dsl.app.features.contains(&"auth-oauth".to_string()) {
            dsl.app.features.push("auth-oauth".to_string());
        }
        Ok(())
    }
}

fn ensure_env() -> Result<()> {
    ensure_env_var("JWT_SECRET", "change_me")?;
    ensure_env_var("REDIS_URL", "redis://localhost:6379")?;
    ensure_env_var("GOOGLE_CLIENT_ID", "")?;
    ensure_env_var("GOOGLE_CLIENT_SECRET", "")?;
    ensure_env_var("GITHUB_CLIENT_ID", "")?;
    ensure_env_var("GITHUB_CLIENT_SECRET", "")?;
    Ok(())
}

fn ensure_templates() -> Result<()> {
    copy_if_missing(
        include_str!("../../../templates/batteries/auth-oauth/backend/handlers/oauth.rs.tera"),
        "backend/handlers/oauth.rs",
    )?;
    copy_if_missing(
        include_str!("../../../templates/batteries/auth-oauth/backend/oauth_clients.rs.tera"),
        "backend/oauth_clients.rs",
    )?;
    copy_if_missing(
        include_str!("../../../templates/batteries/auth-oauth/backend/handlers/policies.rs.tera"),
        "backend/handlers/policies.rs",
    )?;
    copy_if_missing(
        include_str!("../../../templates/batteries/auth-oauth/backend/routes/oauth.rs.tera"),
        "backend/routes/oauth.rs",
    )?;
    copy_if_missing(
        include_str!("../../../templates/batteries/auth-oauth/backend/routes/policies.rs.tera"),
        "backend/routes/policies.rs",
    )?;
    copy_if_missing(
        include_str!(
            "../../../templates/batteries/auth-oauth/frontend/hooks/useOAuthLogin.ts.tera"
        ),
        "frontend/src/hooks/useOAuthLogin.ts",
    )?;
    copy_if_missing(
        include_str!(
            "../../../templates/batteries/auth-oauth/frontend/hooks/useCurrentUserRoles.ts.tera"
        ),
        "frontend/src/hooks/useCurrentUserRoles.ts",
    )?;
    copy_if_missing(
        include_str!(
            "../../../templates/batteries/auth-oauth/frontend/components/OAuthButton.tsx.tera"
        ),
        "frontend/src/components/OAuthButton.tsx",
    )?;
    copy_if_missing(
        include_str!("../../../templates/batteries/auth-oauth/backend/sessions.rs.tera"),
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
