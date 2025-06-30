use super::Plugin;
use anyhow::Result;
use libloading::{Library, Symbol};
use std::path::Path;

/// Wrapper around a dynamically loaded plugin.
pub struct DynamicPlugin {
    _lib: Library,
    inner: Box<dyn Plugin>,
}

impl DynamicPlugin {
    /// Load a dynamic plugin from the given library path.
    pub unsafe fn load<P: AsRef<Path>>(path: P) -> Result<Self> {
        let lib = Library::new(path.as_ref())?;
        let ctor: Symbol<unsafe fn() -> Box<dyn Plugin>> = lib.get(b"plugin_create")?;
        let plugin = ctor();
        Ok(DynamicPlugin {
            _lib: lib,
            inner: plugin,
        })
    }
}

impl Plugin for DynamicPlugin {
    fn name(&self) -> &'static str {
        self.inner.name()
    }

    fn on_init(&self) -> Result<()> {
        self.inner.on_init()
    }

    fn on_compile(&self) -> Result<()> {
        self.inner.on_compile()
    }

    fn extend_dsl(&self, dsl: &mut ferrum_shared_models::FerrumDsl) -> Result<()> {
        self.inner.extend_dsl(dsl)
    }
}
