//! Tokio runtime helpers for asynchronous tasks.
//!
//! In the browser we rely on `wasm_bindgen_futures::spawn_local` instead of a
//! full Tokio runtime, but keeping this module simplifies testing and keeps the
//! API consistent with the desktop version.

/// Spawn a future on the appropriate executor.
pub fn spawn<F>(fut: F)
where
    F: std::future::Future<Output = ()> + 'static,
{
    #[cfg(target_arch = "wasm32")]
    wasm_bindgen_futures::spawn_local(fut);
    #[cfg(not(target_arch = "wasm32"))]
    tokio::spawn(fut);
}

