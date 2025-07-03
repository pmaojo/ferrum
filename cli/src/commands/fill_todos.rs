use anyhow::Result;
use std::path::PathBuf;

pub fn fill_todos(dir: PathBuf) -> Result<()> {
    use dialoguer::Input;
    use regex::Regex;
    use reqwest::blocking::Client;
    use serde_json::json;
    use std::fs;
    use walkdir::WalkDir;

    let re =
        Regex::new(r"// \xE2\x9B\xB3 AI_FILL\[(?P<task>[^\]]+)\] --context=(?P<context>[^\n]+)")
            .unwrap();
    let client = Client::new();

    for entry in WalkDir::new(&dir).into_iter().filter_map(Result::ok) {
        let path = entry.path();
        if path.is_file() {
            if let Ok(contents) = fs::read_to_string(path) {
                if contents.contains("AI_FILL") {
                    let replaced = re.replace_all(&contents, |caps: &regex::Captures| {
                        let task = &caps["task"];
                        let node = &caps["context"];
                        let mut code = client
                            .post("http://localhost:8000/fill-todo")
                            .json(&json!({"code": node, "instructions": task}))
                            .send()
                            .and_then(|r| r.json::<serde_json::Value>())
                            .ok()
                            .and_then(|v| {
                                v.get("code")
                                    .and_then(|v| v.as_str())
                                    .map(|s| s.to_string())
                            })
                            .unwrap_or_default();

                        if code.trim().is_empty() || code.contains("failed to fill") {
                            println!("⚠️  Need more context for {node}");
                            let details: String = Input::new()
                                .with_prompt(&format!("Describe {node}"))
                                .allow_empty(false)
                                .interact_text()
                                .unwrap_or_default();

                            code = client
                                .post("http://localhost:8000/fill-todo")
                                .json(&json!({
                                    "code": node,
                                    "instructions": format!("{}; {}", task, details),
                                }))
                                .send()
                                .and_then(|r| r.json::<serde_json::Value>())
                                .ok()
                                .and_then(|v| {
                                    v.get("code")
                                        .and_then(|v| v.as_str())
                                        .map(|s| s.to_string())
                                })
                                .unwrap_or_else(|| "// failed to fill".to_string());

                            let _ = client
                                .post("http://localhost:8000/node-info")
                                .json(&json!({"id": node, "story": details}))
                                .send();
                        }

                        code
                    });
                    fs::write(path, replaced.as_bytes())?;
                    println!("Filled markers in {}", path.display());
                }
            }
        }
    }
    Ok(())
}

