//! User settings persistence.
//!
//! This module will store UI preferences in `localStorage` on the browser.

/// Placeholder structure for UI configuration.
#[derive(Default, Clone)]
pub struct Settings {
    // TODO: store window layout, theme selection, etc.
    _private: (),
}

