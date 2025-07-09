//! Application state machine used by the UI.
//!
//! The states mirror those from the desktop version but are simplified.

/// High level UI states.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum AppState {
    /// Loading resources or waiting for the backend.
    Loading,
    /// Graph successfully fetched and ready to display.
    Ready,
}

impl Default for AppState {
    fn default() -> Self { AppState::Loading }
}

