//! User settings persistence.
//!
//! Settings such as the window layout and the selected color theme are persisted
//! to browser `localStorage` when running in the web target. The storage
//! mechanism is abstracted behind [`SettingsStore`] so tests can use an
//! in-memory implementation.

use serde::{Deserialize, Serialize};
use thiserror::Error;

/// Available UI themes.
#[derive(Debug, Clone, Copy, Serialize, Deserialize, PartialEq, Eq)]
pub enum Theme {
    /// Light color scheme.
    Light,
    /// Dark color scheme.
    Dark,
}

impl Default for Theme {
    fn default() -> Self { Theme::Light }
}

/// User configurable settings.
#[derive(Debug, Clone, Serialize, Deserialize, PartialEq, Eq)]
pub struct Settings {
    /// Serialized window layout string specific to the UI framework.
    #[serde(default)]
    pub layout: Option<String>,
    /// Selected application theme.
    #[serde(default)]
    pub theme: Theme,
}

impl Default for Settings {
    fn default() -> Self {
        Self { layout: None, theme: Theme::default() }
    }
}

/// Errors returned by [`SettingsStore`] operations.
#[derive(Debug, Error)]
pub enum SettingsError {
    /// Storage backend couldn't be accessed.
    #[error("storage unavailable" )]
    Unavailable,
    /// Failed to (de)serialize settings.
    #[error(transparent)]
    Serde(#[from] serde_json::Error),
}

/// Persistence backend for [`Settings`].
pub trait SettingsStore: Send + Sync {
    /// Load previously stored settings or return [`Settings::default`].
    fn load(&self) -> Result<Settings, SettingsError>;
    /// Save the provided settings.
    fn save(&self, settings: &Settings) -> Result<(), SettingsError>;
}

/// [`SettingsStore`] using browser `localStorage`.
#[cfg(target_arch = "wasm32")]
pub struct LocalStorageStore;

#[cfg(target_arch = "wasm32")]
impl LocalStorageStore {
    const KEY: &'static str = "studio.settings";

    fn storage() -> Result<web_sys::Storage, SettingsError> {
        web_sys::window()
            .and_then(|w| w.local_storage().ok())
            .flatten()
            .ok_or(SettingsError::Unavailable)
    }
}

#[cfg(target_arch = "wasm32")]
impl SettingsStore for LocalStorageStore {
    fn load(&self) -> Result<Settings, SettingsError> {
        let storage = Self::storage()?;
        let value = storage
            .get_item(Self::KEY)
            .map_err(|_| SettingsError::Unavailable)?;
        if let Some(json) = value {
            Ok(serde_json::from_str(&json)?)
        } else {
            Ok(Settings::default())
        }
    }

    fn save(&self, settings: &Settings) -> Result<(), SettingsError> {
        let storage = Self::storage()?;
        let json = serde_json::to_string(settings)?;
        storage
            .set_item(Self::KEY, &json)
            .map_err(|_| SettingsError::Unavailable)
    }
}

/// Simple in-memory [`SettingsStore`] used in tests and native targets.
#[cfg(not(target_arch = "wasm32"))]
pub struct MemoryStore(std::sync::RwLock<Option<Settings>>);

#[cfg(not(target_arch = "wasm32"))]
impl Default for MemoryStore {
    fn default() -> Self { Self(std::sync::RwLock::new(None)) }
}

#[cfg(not(target_arch = "wasm32"))]
impl SettingsStore for MemoryStore {
    fn load(&self) -> Result<Settings, SettingsError> {
        Ok(self.0.read().unwrap().clone().unwrap_or_default())
    }

    fn save(&self, settings: &Settings) -> Result<(), SettingsError> {
        *self.0.write().unwrap() = Some(settings.clone());
        Ok(())
    }
}

