//! Abstract API definition for fetching graph data.
//!
//! This separates HTTP calls from UI logic so implementations can be mocked
//! during tests.

use ferrum_shared_models::FerrumDsl;
use async_trait::async_trait;
use thiserror::Error;
use reqwest_wasm::{Client, Error};

/// Result type for [`GraphApi`] operations that may fail beyond HTTP errors.
pub type ApiResult<T> = Result<T, ApiError>;

/// Error returned by [`GraphApi`] implementations.
#[derive(Debug, Error)]
pub enum ApiError {
    /// HTTP layer failure.
    #[error(transparent)]
    Http(#[from] Error),
    /// Expected `graph` field was missing in server response.
    #[error("missing graph field")]
    MissingGraph,
    /// YAML parsing error when decoding the graph string.
    #[error(transparent)]
    Parse(#[from] serde_yaml::Error),
}

/// API trait used by the components to load and manipulate the graph.
///
/// Implementations should be side-effect free and easy to mock.
#[async_trait(?Send)]
pub trait GraphApi: Send + Sync {
    /// Fetch the current architecture graph as a [`FerrumDsl`].
    async fn fetch_graph(&self) -> ApiResult<FerrumDsl>;

    /// Ask the AI team a question and return the text response.
    async fn ask_ai_team(&self, question: &str) -> reqwest_wasm::Result<String>;

    /// Store optional node information for a given `id` in the backend.
    async fn store_node_info(
        &self,
        id: &str,
        description: Option<&str>,
        story: Option<&str>,
    ) -> reqwest_wasm::Result<()>;

    /// Simulate the provided YAML flow and return textual output.
    async fn simulate_flow(&self, yaml: &str) -> reqwest_wasm::Result<String>;

    /// Generate a component from a prompt in YAML form.
    async fn generate_component(&self, prompt: &str) -> reqwest_wasm::Result<String>;

    /// Validate a YAML snippet, returning `true` when valid.
    async fn validate_yaml(&self, yaml: &str) -> reqwest_wasm::Result<bool>;

    /// Perform an IoT HTTP call to the given `path` in the backend.
    async fn call_iot_http(&self, path: &str) -> reqwest_wasm::Result<String>;

    /// Publish an MQTT message with topic and payload to the backend.
    async fn publish_mqtt(&self, topic: &str, payload: &str) -> reqwest_wasm::Result<()>;

    /// Compile an entire project referenced by `file` and return logs.
    async fn compile_project(&self, file: &str) -> reqwest_wasm::Result<(bool, String)>;

    /// Compile a single module `name` from `file` and return logs.
    async fn compile_module(&self, name: &str, file: &str) -> reqwest_wasm::Result<(bool, String)>;

    /// Compile the provided graph YAML and return logs.
    async fn compile_graph(&self, yaml: &str) -> reqwest_wasm::Result<(bool, String)>;
}

/// HTTP based [`GraphApi`] implementation.
pub struct HttpGraphApi {
    /// Base URL for the backend service.
    base_url: String,
    /// HTTP client reused across API calls.
    client: Client,
}

impl HttpGraphApi {
    /// Create a new instance pointing to the backend `base_url`.
    pub fn new(base_url: impl Into<String>) -> Self {
        Self {
            base_url: base_url.into(),
            client: Client::new(),
        }
    }
}

#[async_trait(?Send)]
impl GraphApi for HttpGraphApi {
    async fn fetch_graph(&self) -> ApiResult<FerrumDsl> {
        let url = format!("{}/graph-rag", self.base_url);
        let res = self
            .client
            .post(&url)
            .json(&serde_json::json!({ "text": "show" }))
            .send()
            .await?;
        let data: serde_json::Value = res.json().await?;
        let graph_str = data
            .get("graph")
            .and_then(|v| v.as_str())
            .ok_or(ApiError::MissingGraph)?;
        let dsl: FerrumDsl = serde_yaml::from_str(graph_str)?;
        Ok(dsl)
    }

    async fn ask_ai_team(&self, question: &str) -> reqwest_wasm::Result<String> {
        let res = self
            .client
            .post(format!("{}/ai-team", self.base_url))
            .json(&serde_json::json!({
                "messages": [{ "role": "user", "content": question }]
            }))
            .send()
            .await?;
        let data: serde_json::Value = res.json().await?;
        Ok(data
            .get("message")
            .and_then(|v| v.as_str())
            .unwrap_or_default()
            .to_string())
    }

    async fn store_node_info(
        &self,
        id: &str,
        description: Option<&str>,
        story: Option<&str>,
    ) -> reqwest_wasm::Result<()> {
        self
            .client
            .post(format!("{}/node-info", self.base_url))
            .json(&serde_json::json!({
                "id": id,
                "description": description,
                "story": story,
            }))
            .send()
            .await?
            .error_for_status()?;
        Ok(())
    }

    async fn simulate_flow(&self, yaml: &str) -> reqwest_wasm::Result<String> {
        let res = self
            .client
            .post(format!("{}/simulate/flow", self.base_url))
            .json(&serde_json::json!({ "yaml": yaml }))
            .send()
            .await?;
        let data: serde_json::Value = res.json().await?;
        Ok(data
            .get("text")
            .and_then(|v| v.as_str())
            .unwrap_or_default()
            .to_string())
    }

    async fn generate_component(&self, prompt: &str) -> reqwest_wasm::Result<String> {
        let res = self
            .client
            .post(format!("{}/generate/component", self.base_url))
            .json(&serde_json::json!({ "text": prompt }))
            .send()
            .await?;
        let data: serde_json::Value = res.json().await?;
        Ok(data
            .get("yaml")
            .and_then(|v| v.as_str())
            .unwrap_or_default()
            .to_string())
    }

    async fn validate_yaml(&self, yaml: &str) -> reqwest_wasm::Result<bool> {
        let res = self
            .client
            .post(format!("{}/validate/yaml", self.base_url))
            .json(&serde_json::json!({ "yaml": yaml }))
            .send()
            .await?;
        let data: serde_json::Value = res.json().await?;
        Ok(data
            .get("valid")
            .and_then(|v| v.as_bool())
            .unwrap_or(false))
    }

    async fn call_iot_http(&self, path: &str) -> reqwest_wasm::Result<String> {
        let res = self
            .client
            .post(format!("{}{}", self.base_url, path))
            .send()
            .await?;
        Ok(res.text().await?)
    }

    async fn publish_mqtt(&self, _topic: &str, _payload: &str) -> reqwest_wasm::Result<()> {
        Ok(())
    }

    async fn compile_project(&self, file: &str) -> reqwest_wasm::Result<(bool, String)> {
        let res = self
            .client
            .post(format!("{}/compile", self.base_url))
            .json(&serde_json::json!({ "file": file }))
            .send()
            .await?;
        let data: serde_json::Value = res.json().await?;
        Ok((
            data.get("ok").and_then(|v| v.as_bool()).unwrap_or(false),
            data.get("logs")
                .and_then(|v| v.as_str())
                .unwrap_or_default()
                .to_string(),
        ))
    }

    async fn compile_module(&self, name: &str, file: &str) -> reqwest_wasm::Result<(bool, String)> {
        let res = self
            .client
            .post(format!("{}/compile/module/{}", self.base_url, name))
            .json(&serde_json::json!({ "file": file }))
            .send()
            .await?;
        let data: serde_json::Value = res.json().await?;
        Ok((
            data.get("ok").and_then(|v| v.as_bool()).unwrap_or(false),
            data.get("logs")
                .and_then(|v| v.as_str())
                .unwrap_or_default()
                .to_string(),
        ))
    }

    async fn compile_graph(&self, yaml: &str) -> reqwest_wasm::Result<(bool, String)> {
        let res = self
            .client
            .post(format!("{}/compile/graph", self.base_url))
            .json(&serde_json::json!({ "yaml": yaml }))
            .send()
            .await?;
        let data: serde_json::Value = res.json().await?;
        Ok((
            data.get("ok").and_then(|v| v.as_bool()).unwrap_or(false),
            data.get("logs")
                .and_then(|v| v.as_str())
                .unwrap_or_default()
                .to_string(),
        ))
    }
} 