//! Abstract API definition for fetching graph data.
//!
//! This separates HTTP calls from UI logic so implementations can be mocked
//! during tests.

use ferrum_shared_models::{FerrumDsl, DslApp};

/// API trait used by the components to load and manipulate the graph.
///
/// Implementations should be side-effect free and easy to mock.
pub trait GraphApi {
    /// Fetch the current architecture graph as a [`FerrumDsl`].
    fn fetch_graph(&self) -> std::pin::Pin<Box<dyn std::future::Future<Output = reqwest::Result<FerrumDsl>> + '_>>;

    // TODO: add async methods mirroring studio-desktop's API such as:
    // - ask_ai_team(&self, question: &str)
    // - store_node_info(&self, id: &str, description: Option<&str>, story: Option<&str>)
    // - simulate_flow(&self, yaml: &str)
    // - generate_component(&self, prompt: &str)
    // - validate_yaml(&self, yaml: &str)
    // - call_iot_http(&self, path: &str)
    // - publish_mqtt(&self, topic: &str, payload: &str)
    // - compile_project(&self, file: &str)
    // - compile_module(&self, name: &str, file: &str)
    // - compile_graph(&self, yaml: &str)
    // Each method should return a `reqwest::Result<T>` and be documented.
}

/// HTTP based [`GraphApi`] implementation.
pub struct HttpGraphApi {
    base_url: String,
}

impl HttpGraphApi {
    /// Create a new instance pointing to the backend `base_url`.
    pub fn new(base_url: impl Into<String>) -> Self {
        Self { base_url: base_url.into() }
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

