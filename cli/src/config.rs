use serde::Deserialize;
use std::fs;
use std::path::Path;

#[derive(Debug, Deserialize)]
pub struct LlmConfig {
    pub model: Option<String>,
    pub openai: Option<OpenAi>,
    pub ollama: Option<Ollama>,
}

#[derive(Debug, Deserialize)]
pub struct OpenAi {
    pub api_key: Option<String>,
}

#[derive(Debug, Deserialize)]
pub struct Ollama {
    pub endpoint: Option<String>,
}

impl LlmConfig {
    /// Load configuration from `llm-config.yaml` if present.
    pub fn load() -> Option<Self> {
        let path = Path::new("llm-config.yaml");
        if path.exists() {
            let contents = fs::read_to_string(path).ok()?;
            serde_yaml::from_str(&contents).ok()
        } else {
            None
        }
    }
}
