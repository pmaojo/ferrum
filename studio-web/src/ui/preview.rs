//! Preview utilities for the generated frontend.
//!
//! Provides a pluggable [`PreviewOpener`] so the preview logic can be mocked
//! during tests.

/// Trait used to open the generated frontend.
pub trait PreviewOpener: Send + Sync {
    /// Open the provided `url` for preview.
    fn open(&self, url: &str);
}

/// Default preview opener using the current platform facilities.
pub struct DefaultPreviewOpener;

impl PreviewOpener for DefaultPreviewOpener {
    fn open(&self, url: &str) {
        #[cfg(target_arch = "wasm32")]
        {
            if let Some(win) = web_sys::window() {
                let _ = win.open_with_url(url);
            }
        }
        #[cfg(not(target_arch = "wasm32"))]
        {
            let _ = webbrowser::open(url);
        }
    }
}
