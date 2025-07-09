//! Web-based Studio built with Leptos.
//!
//! Components are separated from data-fetching logic via the [`GraphApi`] trait
//! to ease testing and allow mocked implementations.

use leptos::*;
use ferrum_shared_models::{FerrumDsl, DslApp};

/// Trait describing the required API for fetching the graph data.
/// This abstraction allows mocking in tests and swapping implementations.
pub trait GraphApi {
    /// Fetch the graph as a [`FerrumDsl`] from the backend service.
    fn fetch_graph(&self) -> std::pin::Pin<Box<dyn std::future::Future<Output = reqwest::Result<FerrumDsl>> + '_>>;
}

/// HTTP-based [`GraphApi`] implementation using `reqwest`.
pub struct HttpGraphApi {
    base_url: String,
}

impl HttpGraphApi {
    /// Create a new instance targeting the given base URL.
    pub fn new(base_url: impl Into<String>) -> Self {
        Self {
            base_url: base_url.into(),
        }
    }
}

impl GraphApi for HttpGraphApi {
    fn fetch_graph(&self) -> std::pin::Pin<Box<dyn std::future::Future<Output = reqwest::Result<FerrumDsl>> + '_>> {
        let url = format!("{}/graph-rag", self.base_url);
        Box::pin(async move {
            let res = reqwest::Client::new()
                .post(&url)
                .json(&serde_json::json!({ "text": "show" }))
                .send()
                .await?;
            let data: serde_json::Value = res.json().await?;
            let graph_str = data.get("graph").and_then(|v| v.as_str()).unwrap_or("{}");
            let dsl: FerrumDsl = serde_yaml::from_str(graph_str).unwrap_or_else(|_| FerrumDsl {
                app: DslApp {
                    name: "empty".into(),
                    title: None,
                    version: None,
                    database: None,
                    features: vec![],
                    auth: None,
                },
                modules: Default::default(),
                routes: vec![],
                pages: vec![],
                components: vec![],
                queries: vec![],
                mutations: vec![],
                jobs: vec![],
                entities: vec![],
                forms: vec![],
                validations: vec![],
                uploads: vec![],
                policies: vec![],
                resources: vec![],
                iot: vec![],
            });
            Ok(dsl)
        })
    }
}

/// Global [`HttpGraphApi`] used by the Leptos components.
static API: once_cell::sync::Lazy<HttpGraphApi> = once_cell::sync::Lazy::new(|| {
    let url = std::env::var("FERRUM_API_BASE_URL").unwrap_or_else(|_| "http://localhost:8001".into());
    HttpGraphApi::new(url)
});

/// Root component for the web studio.
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

