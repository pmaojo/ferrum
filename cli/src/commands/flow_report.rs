use anyhow::{Context, Result};
use std::path::PathBuf;

pub fn flow_report(file: PathBuf) -> Result<()> {
    use reqwest::blocking::Client;
    use std::fs;

    let yaml = fs::read_to_string(&file)
        .with_context(|| format!("Failed to read file: {}", file.display()))?;
    let client = Client::new();
    let resp = client
        .post("http://localhost:8001/simulate/flow")
        .json(&serde_json::json!({ "yaml": yaml }))
        .send()
        .with_context(|| "Failed to connect to AI service. Is it running?")?;

    if !resp.status().is_success() {
        println!("⚠️  AI service responded with status {}", resp.status());
        return Err(anyhow::anyhow!("AI service error"));
    }

    let value: serde_json::Value = resp
        .json()
        .with_context(|| "Failed to parse response from AI service")?;
    let text = value.get("text").and_then(|v| v.as_str()).unwrap_or("");

    println!("{}", text);
    Ok(())
}

