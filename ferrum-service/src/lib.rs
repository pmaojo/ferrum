//! Ferrum service layer.
//!
//! This crate exposes reusable logic shared across the CLI and
//! future HTTP backends. All CLI commands are re-exported for
//! convenience.

pub use ferrum_cli::commands::*;

pub mod helpers {
    //! Collection of small utilities used across services.
    pub mod logging;
    pub mod streaming;
    pub mod auth;
}
