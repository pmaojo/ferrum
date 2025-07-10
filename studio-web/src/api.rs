//! Abstract API definition for fetching graph data.
//!
//! This separates HTTP calls from UI logic so implementations can be mocked
//! during tests.

use ferrum_shared_models::FerrumDsl;
use async_trait::async_trait;
use thiserror::Error;

/// Result type for [`GraphApi`] operations that may fail beyond HTTP errors.
pub type ApiResult<T> = Result<T, ApiError>;

/// Error returned by [`GraphApi`] implementations.
#[derive(Debug, Error)]
pub enum ApiError {
    /// HTTP layer failure.
    #[error(transparent)]
    Http(#[from] reqwest::Error),
    /// Expected `graph` field was missing in server response.
    #[error("missing graph field")] 
    MissingGraph,
    /// YAML parsing error when decoding the graph string.
    #[error(transparent)]
    Parse(#[from] serde_yaml::Error),
}

/// Result type returned by [`GraphApi`] implementations.
pub type ApiResult<T> = Result<T, ApiError>;

/// Errors that can occur when interacting with the API.
#[derive(thiserror::Error, Debug)]
pub enum ApiError {
    /// An underlying HTTP error.
    #[error(transparent)]
    Http(#[from] reqwest::Error),
    /// Returned when the backend response is missing the `graph` field.
    #[error("missing 'graph' field in response" )]
    MissingGraph,
    /// Graph YAML parsing failed.
    #[error(transparent)]
    Parse(#[from] serde_yaml::Error),
}

/// API trait used by the components to load and manipulate the graph.
///
/// Implementations should be side-effect free and easy to mock.
#[async_trait]
pub trait GraphApi {
    /// Fetch the current architecture graph as a [`FerrumDsl`].
    async fn fetch_graph(&self) -> ApiResult<FerrumDsl>;

    /// Ask the AI team a question and return the text response.
    async fn ask_ai_team(&self, question: &str) -> reqwest::Result<String>;

    /// Store optional node information for a given `id`.
    async fn store_node_info(
        &self,
        id: &str,
        description: Option<&str>,
        story: Option<&str>,
    ) -> reqwest::Result<()>;

    /// Simulate the provided YAML flow and return textual output.
    async fn simulate_flow(&self, yaml: &str) -> reqwest::Result<String>;

    /// Generate a component from a prompt in YAML form.
    async fn generate_component(&self, prompt: &str) -> reqwest::Result<String>;

    /// Validate a YAML snippet, returning `true` when valid.
    async fn validate_yaml(&self, yaml: &str) -> reqwest::Result<bool>;

    /// Perform an IoT HTTP call to the given `path`.
    async fn call_iot_http(&self, path: &str) -> reqwest::Result<String>;

    /// Publish an MQTT message with topic and payload.
    async fn publish_mqtt(&self, topic: &str, payload: &str) -> reqwest::Result<()>;

    /// Compile an entire project referenced by `file`.
    async fn compile_project(&self, file: &str) -> reqwest::Result<(bool, String)>;

    /// Compile a single module `name` from `file`.
    async fn compile_module(&self, name: &str, file: &str) -> reqwest::Result<(bool, String)>;

    /// Compile the provided graph YAML.
    async fn compile_graph(&self, yaml: &str) -> reqwest::Result<(bool, String)>;
}

/// HTTP based [`GraphApi`] implementation.
pub struct HttpGraphApi {
    /// Base URL for the backend service.
    base_url: String,
    /// HTTP client reused across API calls.
    client: reqwest::Client,
}

impl HttpGraphApi {
    /// Create a new instance pointing to the backend `base_url`.
    pub fn new(base_url: impl Into<String>) -> Self {
        Self {
            base_url: base_url.into(),
            client: reqwest::Client::new(),
        }
    }
}

#[async_trait]
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

    async fn ask_ai_team(&self, question: &str) -> reqwest::Result<String> {
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
    ) -> reqwest::Result<()> {
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

    async fn simulate_flow(&self, yaml: &str) -> reqwest::Result<String> {
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

    async fn generate_component(&self, prompt: &str) -> reqwest::Result<String> {
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

    async fn validate_yaml(&self, yaml: &str) -> reqwest::Result<bool> {
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

    async fn call_iot_http(&self, path: &str) -> reqwest::Result<String> {
        let res = self
            .client
            .post(format!("{}{}", self.base_url, path))
            .send()
            .await?;
        Ok(res.text().await?)
    }

    async fn publish_mqtt(&self, _topic: &str, _payload: &str) -> reqwest::Result<()> {
        Ok(())
    }

    async fn compile_project(&self, file: &str) -> reqwest::Result<(bool, String)> {
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

    async fn compile_module(&self, name: &str, file: &str) -> reqwest::Result<(bool, String)> {
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

    async fn compile_graph(&self, yaml: &str) -> reqwest::Result<(bool, String)> {
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

