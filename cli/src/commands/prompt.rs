use anyhow::Result;
use std::path::PathBuf;

pub fn prompt(text: String, output: Option<PathBuf>) -> Result<()> {
    use crate::config::LlmConfig;
    use reqwest::blocking::Client;
    use std::fs;

    println!("🤖 AI Architecture Generation");
    println!("━━━━━━━━━━━━━━━━━━━━━━━━━━━━");
    println!("Prompt: {}", text);
    println!();

    // Determine model from env or llm-config.yaml
    let cfg_model = LlmConfig::load().and_then(|c| c.model);
    let model = std::env::var("MODEL")
        .ok()
        .or(cfg_model)
        .unwrap_or_else(|| "openai".to_string());

    // Call Python AI service
    let client = Client::new();
    let response = client
        .post("http://localhost:8001/generate-yaml")
        .json(&serde_json::json!({ "text": text, "model": model }))
        .send()?;

    let yaml = response
        .json::<serde_json::Value>()?
        .get("yaml")
        .and_then(|v| v.as_str())
        .unwrap_or("module: generated\nnodes: []")
        .to_string();

    let output_path = output.unwrap_or_else(|| PathBuf::from("gen/generated.yaml"));
    fs::create_dir_all(output_path.parent().unwrap())?;
    fs::write(&output_path, yaml)?;

    println!(
        "✅ Architecture graph generated at: {}",
        output_path.display()
    );
    println!(
        "ℹ️  Run 'ferrum compile {}' to generate code from this architecture",
        output_path.display()
    );

    Ok(())
}
