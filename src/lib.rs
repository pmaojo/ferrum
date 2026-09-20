//! Facade crate for the Ferrum workspace.
//!
//! The workspace root package exists so `ferrum` resolves as a library name;
//! the real implementation lives in the member crates. Re-exporting them here
//! keeps the root target compiling against the root manifest's own dependency
//! list instead of silently borrowing `ferrum-cli`'s sources, which the root
//! package does not declare dependencies for.
pub use ferrum_cli as cli;
pub use ferrum_engine as engine;
pub use ferrum_service as service;
