use webbrowser;
#[cfg(target_arch = "wasm32")]
use web_sys::window;

/// Interface to present compiled frontend to the user.
pub trait Previewer: Send + Sync {
    /// Show the generated index.html located at `path`.
    fn show(&self, path: &str);
}

/// Default [`Previewer`] opening the file in a new browser window on WASM or the
/// native system browser when running natively.
pub struct WindowPreviewer;

impl Previewer for WindowPreviewer {
    fn show(&self, path: &str) {
        #[cfg(target_arch = "wasm32")]
        if let Some(win) = window() {
            let _ = win.open_with_url(path);
        }

        #[cfg(not(target_arch = "wasm32"))]
        let _ = webbrowser::open(path);
    }
}
