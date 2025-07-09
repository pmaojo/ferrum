//! Leptos application entry points.
//!
//! This module wires components with the [`GraphApi`] implementation.

use leptos::*;
use crate::api::{GraphApi, HttpGraphApi};

/// Shared [`GraphApi`] used across components.
static API: once_cell::sync::Lazy<HttpGraphApi> = once_cell::sync::Lazy::new(|| {
    let url = std::env::var("FERRUM_API_BASE_URL").unwrap_or_else(|_| "http://localhost:8001".into());
    HttpGraphApi::new(url)
});

/// Root application component.
#[component]
pub fn App() -> impl IntoView {
    let graph = create_local_resource(|| (), |_| async move {
        API.fetch_graph().await.map_err(|e| e.to_string())
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

