//! Logging helpers.
//!
//! Provides a simple initialization routine for the global tracer.

use tracing::Level;

/// Initialize a default `tracing` subscriber.
///
/// Subsequent calls are ignored so this can safely be used in tests.
pub fn init(level: Level) {
    let _ = tracing_subscriber::fmt()
        .with_max_level(level)
        .with_target(false)
        .try_init();
}
