use anyhow::Result;
use std::fs;
use std::path::Path;

use ferrum_shared_models::FerrumDsl;

use super::Plugin;

/// Experimental auth plugin that scaffolds basic authentication support.
pub struct AuthPlugin;

impl Plugin for AuthPlugin {
    fn name(&self) -> &'static str {
        "auth"
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
    let path = Path::new(".env");
    if !path.exists() {
        let content = "JWT_SECRET=change_me\nAUTH_REDIRECT=/login\n";
        fs::write(path, content)?;
    }
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
