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
pub mod runtime;
pub mod ui;

pub use api::{GraphApi, HttpGraphApi};
pub use app::{App, compile_project_and_preview, set_api, set_preview_opener};
