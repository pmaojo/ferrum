//! Leptos application entry points.
//!
//! This module wires components with the [`GraphApi`] implementation.

use leptos::*;
use crate::api::{GraphApi, HttpGraphApi};
use std::sync::RwLock;

/// Shared [`GraphApi`] used across components.
static API: once_cell::sync::Lazy<RwLock<Box<dyn GraphApi>>> = once_cell::sync::Lazy::new(|| {
    let url = std::env::var("FERRUM_API_BASE_URL").unwrap_or_else(|_| "http://localhost:8001".into());
    RwLock::new(Box::new(HttpGraphApi::new(url)))
});

#[cfg(any(test, feature = "test-api"))]
/// Replace the global [`GraphApi`] instance.
pub fn set_api(api: Box<dyn GraphApi>) {
    let mut writer = API.write().expect("API lock");
    *writer = api;
}

/// Root application component.
#[component]
pub fn App() -> impl IntoView {
    let graph = create_local_resource(|| (), |_| async move {
        let api = API.read().expect("API lock");
        api.fetch_graph().await.map_err(|e| e.to_string())
    });

    view! {
        <div class="studio">
            <h1>"Ferrum Studio"</h1>
            {move || match graph.get() {
                Some(Ok(dsl)) => view! { <pre>{format!("{:?}", dsl)}</pre> }.into_view(),
                Some(Err(e)) => view! { <span>{format!("Error: {}", e)}</span> }.into_view(),
                None => view! { <span>"Loading..."</span> }.into_view(),
            }}
        </div>
    }
}

