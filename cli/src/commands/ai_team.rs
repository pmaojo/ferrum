use anyhow::Result;

pub fn ai_team(text: String) -> Result<()> {
    use crate::config::LlmConfig;
    use atty::Stream;
    use reqwest::blocking::Client;
    use std::io::{self, Read};

    let cfg_model = LlmConfig::load().and_then(|c| c.model);
    let model = std::env::var("MODEL")
        .ok()
        .or(cfg_model)
        .unwrap_or_else(|| "openai".to_string());

    let mut prompt = text;
    if !atty::is(Stream::Stdin) {
        let mut buf = String::new();
        io::stdin().read_to_string(&mut buf)?;
        if !buf.trim().is_empty() {
            prompt.push_str("\n");
            prompt.push_str(&buf);
        }
    }

    let client = Client::new();
    let resp = client
        .post("http://localhost:8000/ai-team")
        .json(&serde_json::json!({
            "messages": [{"role": "user", "content": prompt}],
            "model": model,
        }))
        .send()?;

    let value = resp.json::<serde_json::Value>()?;
    let reply = value.get("message").and_then(|v| v.as_str()).unwrap_or("");

    println!("{}", reply);
    Ok(())
}

