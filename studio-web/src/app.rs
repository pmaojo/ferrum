//! Leptos application entry points.
//!
//! This module wires components with the [`GraphApi`] implementation.

use leptos::*;
use crate::api::{GraphApi, HttpGraphApi};
use crate::preview::{Previewer, WindowPreviewer, INDEX_HTML};
use wasm_bindgen_futures::spawn_local;
use reqwest_wasm::Result;
use std::sync::RwLock;

/// Shared [`GraphApi`] used across components.
static API: once_cell::sync::Lazy<RwLock<std::sync::Arc<dyn GraphApi>>> = once_cell::sync::Lazy::new(|| {
    let url = std::env::var("FERRUM_API_BASE_URL").unwrap_or_else(|_| "http://localhost:8001".into());
    RwLock::new(std::sync::Arc::new(HttpGraphApi::new(url)))
});

/// Shared [`Previewer`] used to display compiled apps.
static PREVIEWER: once_cell::sync::Lazy<RwLock<std::sync::Arc<dyn Previewer>>> = once_cell::sync::Lazy::new(|| {
    RwLock::new(std::sync::Arc::new(WindowPreviewer))
});

/// Replace the global [`GraphApi`] instance.
pub fn set_api(api: std::sync::Arc<dyn GraphApi>) {
    let mut writer = API.write().expect("API lock");
    *writer = api;
}

/// Replace the global [`Previewer`] instance.
pub fn set_previewer(previewer: std::sync::Arc<dyn Previewer>) {
    let mut writer = PREVIEWER.write().expect("PREVIEWER lock");
    *writer = previewer;
}

/// Compile the given `file` and show the generated frontend when successful.
/// Compile `file` using [`GraphApi::compile_project`] and show the generated
/// [`INDEX_HTML`] when successful.
pub async fn compile_and_preview(file: &str) -> Result<()> {
    let api = {
        let reader = API.read().expect("API lock");
        reader.clone()
    };
    let (ok, _logs) = api.compile_project(file).await?;
    if ok {
        let previewer = {
            let reader = PREVIEWER.read().expect("PREVIEWER lock");
            reader.clone()
        };
        previewer.show(INDEX_HTML);
    }
    Ok(())
}

/// Root application component.
#[component]
pub fn App() -> impl IntoView {
    let graph = create_local_resource(|| (), |_| async move {
        let api = {
            let reader = API.read().expect("API lock");
            reader.clone()
        };
        api.fetch_graph().await.map_err(|e| e.to_string())
    });

    view! {
        <div class="studio">
            <h1>"Ferrum Studio"</h1>
            <button on:click=move |_| {
                spawn_local(async {
                    let _ = compile_and_preview("project.yaml").await;
                });
            }>
                "Build & Preview"
            </button>
            {move || match graph.get() {
                Some(Ok(dsl)) => view! { <pre>{format!("{:?}", dsl)}</pre> }.into_view(),
                Some(Err(e)) => view! { <span>{format!("Error: {}", e)}</span> }.into_view(),
                None => view! { <span>"Loading..."</span> }.into_view(),
            }}
        </div>
    }
}

