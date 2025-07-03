use anyhow::Result;
use std::path::PathBuf;

pub fn flow_report(file: PathBuf) -> Result<()> {
    use reqwest::blocking::Client;
    use std::fs;

    let yaml = fs::read_to_string(&file)?;
    let client = Client::new();
    let resp = client
        .post("http://localhost:8000/simulate/flow")
        .json(&serde_json::json!({ "yaml": yaml }))
        .send()?;

    let value: serde_json::Value = resp.json()?;
    let text = value.get("text").and_then(|v| v.as_str()).unwrap_or("");

    println!("{}", text);
    Ok(())
}

