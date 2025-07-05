use anyhow::{Context, Result};
use std::path::PathBuf;

/// Default regex pattern used to locate AI_FILL markers.
pub const TODO_PATTERN: &str =
    r"// \xE2\x9B\xB3 AI_FILL\[(?P<task>[^\]]+)\] --context=(?P<context>[^\n]+)";

/// Public interface used by the CLI.
pub fn fill_todos(dir: PathBuf, ai_url: &str) -> Result<()> {
    fill_todos_with_pattern(dir, TODO_PATTERN, ai_url)
}

/// Implementation that allows supplying a custom regex pattern.
/// Exposed for testing to validate regex failure handling.
pub fn fill_todos_with_pattern(dir: PathBuf, pattern: &str, ai_url: &str) -> Result<()> {
    use dialoguer::Input;
    use regex::Regex;
    use reqwest::blocking::Client;
    use serde_json::json;
    use std::fs;
    use walkdir::WalkDir;

    let re = Regex::new(pattern).context("Invalid regex pattern")?;
    let client = Client::new();
    let base = ai_url.trim_end_matches('/');
    let fill_todo_url = format!("{}/fill-todo", base);
    let node_info_url = format!("{}/node-info", base);

    for entry in WalkDir::new(&dir).into_iter().filter_map(Result::ok) {
        let path = entry.path();
        if path.is_file() {
            if let Ok(contents) = fs::read_to_string(path) {
                if contents.contains("AI_FILL") {
                    let replaced = re.replace_all(&contents, |caps: &regex::Captures| {
                        let task = &caps["task"];
                        let node = &caps["context"];
                        let mut code = client
                            .post(&fill_todo_url)
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
                                .post(&fill_todo_url)
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
                                .post(&node_info_url)
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

