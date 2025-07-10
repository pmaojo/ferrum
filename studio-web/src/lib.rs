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
pub mod preview;

pub use api::{GraphApi, HttpGraphApi};
pub use app::App;
pub use app::compile_and_preview;
pub use preview::{Previewer, WindowPreviewer};
pub use preview::INDEX_HTML;
pub use app::{set_api, set_previewer};


