use anyhow::Result;
use std::path::PathBuf;

pub fn component_prompt(text: String, output: Option<PathBuf>) -> Result<()> {
    use crate::config::LlmConfig;
    use reqwest::blocking::Client;
    use std::fs;

    println!("🤖 AI Component Generation");
    println!("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━");
    println!("Prompt: {}", text);
    println!();

    let cfg_model = LlmConfig::load().and_then(|c| c.model);
    let model = std::env::var("MODEL")
        .ok()
        .or(cfg_model)
        .unwrap_or_else(|| "openai".to_string());

    let client = Client::new();
    let response = client
        .post("http://localhost:8000/generate-component")
        .json(&serde_json::json!({ "text": text, "model": model }))
        .send()?;

    let yaml = response
        .json::<serde_json::Value>()?
        .get("yaml")
        .and_then(|v| v.as_str())
        .unwrap_or("components: []")
        .to_string();

    let output_path = output.unwrap_or_else(|| PathBuf::from("gen/component.yaml"));
    fs::create_dir_all(output_path.parent().unwrap())?;
    fs::write(&output_path, yaml)?;

    println!("✅ Component YAML generated at: {}", output_path.display());

    Ok(())
}
