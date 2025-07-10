//! Web-based Studio built with Leptos.
//!
//! The crate mirrors the structure of `studio-desktop` but targets the browser.
//! Most modules are currently placeholders documenting the intended flow.

pub mod api;
pub mod app;
// TODO: expose additional modules mirroring the desktop UI:
pub mod graph;
pub mod viewer;
pub mod app_state;
pub mod settings;

pub use api::{GraphApi, HttpGraphApi};
pub use app::App;

#[cfg(any(test, feature = "test-api"))]
pub use app::set_api;

