use anyhow::Result;
use std::fs;
use std::path::Path;

use ferrum_shared_models::FerrumDsl;

use super::Plugin;

/// Plugin that scaffolds OAuth authentication with Google and GitHub.
pub struct AuthOAuthPlugin;

impl Plugin for AuthOAuthPlugin {
    fn name(&self) -> &'static str {
        "auth-oauth"
    }

    fn on_init(&self) -> Result<()> {
        ensure_templates()?;
        ensure_env()
    }

    fn on_compile(&self) -> Result<()> {
        ensure_templates()?;
        ensure_env()
    }

    fn extend_dsl(&self, dsl: &mut FerrumDsl) -> Result<()> {
        if !dsl.app.features.contains(&"auth-oauth".to_string()) {
            dsl.app.features.push("auth-oauth".to_string());
        }
        Ok(())
    }
}

fn ensure_env() -> Result<()> {
    let path = Path::new(".env");
    if !path.exists() {
        let content = "JWT_SECRET=change_me\nREDIS_URL=redis://localhost:6379\nGOOGLE_CLIENT_ID=\nGOOGLE_CLIENT_SECRET=\nGITHUB_CLIENT_ID=\nGITHUB_CLIENT_SECRET=\n";
        fs::write(path, content)?;
    }
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
