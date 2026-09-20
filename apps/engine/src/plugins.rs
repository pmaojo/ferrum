use anyhow::Result;
use std::path::Path;
use ferrum_shared_models::FerrumDsl;

/// Small filesystem helpers shared by plugin `init`/`compile` steps: writing
/// a scaffold file only if the user hasn't already customized it, and
/// idempotently declaring a crate dependency the plugin needs.
pub mod utils {
    use anyhow::Result;
    use std::fs;
    use std::path::Path;

    /// Write `content` to `path` unless something is already there.
    ///
    /// Plugin `init` steps run after the base scaffold, so a file may
    /// already have been generated (or hand-edited) by the time a plugin
    /// wants to drop in its own version; overwriting it would silently
    /// discard that.
    pub fn copy_if_missing(content: &str, path: &Path) -> Result<()> {
        if path.exists() {
            return Ok(());
        }
        if let Some(parent) = path.parent() {
            fs::create_dir_all(parent)?;
        }
        fs::write(path, content)?;
        Ok(())
    }

    /// Idempotently declare `name = "version"` in `backend/Cargo.toml`'s
    /// dependency table, relative to the current directory.
    ///
    /// This is a plain text append rather than a TOML-aware edit: plugin
    /// `Cargo.toml` edits only ever add a bare `name = "version"` line, and
    /// keeping this dependency-free of a TOML crate keeps the engine crate
    /// light. Callers that need structured edits (features, tables) should
    /// go through `toml::Value` themselves, as `ferrum-cli`'s `init` does.
    pub fn ensure_dep(name: &str, version: &str) -> Result<()> {
        let path = Path::new("backend/Cargo.toml");
        let mut content = fs::read_to_string(path)?;
        if content.contains(name) {
            return Ok(());
        }
        if !content.ends_with('\n') {
            content.push('\n');
        }
        content.push_str(&format!("{name} = \"{version}\"\n"));
        fs::write(path, content)?;
        Ok(())
    }
}

pub struct PluginMetadata {
    pub library: String,
}

impl PluginMetadata {
    pub fn from_file(_path: &Path) -> Result<Self> {
        Ok(PluginMetadata {
            library: " ".to_string(),
        })
    }
}

pub struct DynamicPlugin;

impl DynamicPlugin {
    pub fn load(_path: &Path) -> Result<Self> {
        Ok(DynamicPlugin)
    }
}

pub struct GraphQLPlugin;
pub struct AuthPlugin;
pub struct AuthPasswordPlugin;
pub struct AuthOAuthPlugin;
pub struct StripePlugin;
pub struct CronPlugin;
pub struct CmsSanityPlugin;
pub struct CmsNotionPlugin;
pub struct RealtimeSsePlugin;

#[derive(Default)]
pub struct PluginManager;

impl PluginManager {
    pub fn new() -> Self {
        PluginManager
    }

    pub fn register<T>(&mut self, _plugin: T) {
        // TODO: Implement plugin registration
    }

    pub fn compile_all(&self) -> Result<()> {
        Ok(())
    }

    pub fn extend_dsl_all(&self, _dsl: &mut FerrumDsl) -> Result<()> {
        Ok(())
    }

    pub fn init_all(&self) -> Result<()> {
        Ok(())
    }
}
