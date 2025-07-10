//! Leptos application entry points.
//!
//! This module wires components with the [`GraphApi`] implementation.

use leptos::*;
use crate::api::{GraphApi, HttpGraphApi};
use crate::ui::preview::{DefaultPreviewOpener, PreviewOpener};
use std::sync::RwLock;

/// Shared [`GraphApi`] used across components.
static API: once_cell::sync::Lazy<RwLock<Box<dyn GraphApi>>> = once_cell::sync::Lazy::new(|| {
    let url = std::env::var("FERRUM_API_BASE_URL").unwrap_or_else(|_| "http://localhost:8001".into());
    RwLock::new(Box::new(HttpGraphApi::new(url)))
});

/// [`PreviewOpener`] used to show the compiled frontend.
static PREVIEW_OPENER: once_cell::sync::Lazy<RwLock<Box<dyn PreviewOpener>>> =
    once_cell::sync::Lazy::new(|| RwLock::new(Box::new(DefaultPreviewOpener)));

/// Replace the global [`GraphApi`] instance.
pub fn set_api(api: Box<dyn GraphApi>) {
    let mut writer = API.write().expect("API lock");
    *writer = api;
}

/// Replace the global [`PreviewOpener`] instance.
pub fn set_preview_opener(opener: Box<dyn PreviewOpener>) {
    let mut writer = PREVIEW_OPENER.write().expect("opener lock");
    *writer = opener;
}

/// Compile the project referenced by `file` and preview the generated frontend.
pub async fn compile_project_and_preview(file: &str) -> reqwest_wasm::Result<(bool, String)> {
    let (ok, logs) = {
        let api = API.read().expect("API lock");
        api.compile_project(file).await?
    };
    if ok {
        let base = std::env::var("FERRUM_API_BASE_URL")
            .unwrap_or_else(|_| "http://localhost:8001".into());
        let url = format!("{}/frontend/index.html", base);
        let opener = PREVIEW_OPENER.read().expect("opener lock");
        opener.open(&url);
    }
    Ok((ok, logs))
}

/// Root application component.
#[component]
pub fn App() -> impl IntoView {
    let graph = create_local_resource(|| (), |_| async move {
        let api = API.read().expect("API lock");
        api.fetch_graph().await.map_err(|e| e.to_string())
    });

    let compiling = create_rw_signal(false);

    #[cfg(target_arch = "wasm32")]
    let on_compile = move |_| {
        compiling.set(true);
        leptos::spawn_local(async move {
            let _ = compile_project_and_preview("dsl.yaml").await;
            compiling.set(false);
        });
    };

    #[cfg(not(target_arch = "wasm32"))]
    let on_compile = move |_| {
        let _ = compiling;
    };

    view! {
        <div class="studio">
            <h1>"Ferrum Studio"</h1>
            <button on:click=on_compile disabled=move || compiling.get()>"Compile"</button>
            {move || match graph.get() {
                Some(Ok(dsl)) => view! { <pre>{format!("{:?}", dsl)}</pre> }.into_view(),
                Some(Err(e)) => view! { <span>{format!("Error: {}", e)}</span> }.into_view(),
                None => view! { <span>"Loading..."</span> }.into_view(),
            }}
        </div>
    }
}

