use once_cell::sync::OnceCell;
use serde::{Deserialize, Serialize};
use std::sync::mpsc::Sender;

static LOG_SENDER: OnceCell<Sender<String>> = OnceCell::new();

pub fn set_log_sender(sender: Sender<String>) {
    let _ = LOG_SENDER.set(sender);
}

pub fn push_log<S: Into<String>>(msg: S) {
    if let Some(tx) = LOG_SENDER.get() {
        let _ = tx.send(msg.into());
    }
}

fn log(msg: String) {
    if let Some(tx) = LOG_SENDER.get() {
        let _ = tx.send(msg);
    }
}

#[derive(Serialize)]
struct PromptRequest<'a> {
    text: &'a str,
}

#[derive(Deserialize)]
struct GraphResponse {
    graph: String,
}

#[derive(Serialize)]
struct ChatRequest<'a> {
    messages: [Message<'a>; 1],
}

#[derive(Serialize)]
struct Message<'a> {
    role: &'a str,
    content: &'a str,
}

#[derive(Deserialize)]
struct ChatResponse {
    message: String,
}

pub async fn fetch_graph(question: &str) -> reqwest::Result<String> {
    log(format!("[API] POST /graph-rag {question}"));
    let client = reqwest::Client::new();
    let res = client
        .post("http://localhost:8001/graph-rag")
        .json(&PromptRequest { text: question })
        .send()
        .await?;
    let data: GraphResponse = res.json().await?;
    Ok(data.graph)
}

pub async fn ask_ai_team(question: &str) -> reqwest::Result<String> {
    log(format!("[API] POST /ai-team {question}"));
    let client = reqwest::Client::new();
    let res = client
        .post("http://localhost:8001/ai-team")
        .json(&ChatRequest {
            messages: [Message {
                role: "user",
                content: question,
            }],
        })
        .send()
        .await?;
    let data: ChatResponse = res.json().await?;
    Ok(data.message)
}

#[derive(Serialize)]
struct NodeInfoRequest<'a> {
    id: &'a str,
    #[serde(skip_serializing_if = "Option::is_none")]
    description: Option<&'a str>,
    #[serde(skip_serializing_if = "Option::is_none")]
    story: Option<&'a str>,
}

#[derive(Deserialize)]
struct NodeInfoResponse {
    ok: bool,
}

pub async fn store_node_info(
    id: &str,
    description: Option<&str>,
    story: Option<&str>,
) -> reqwest::Result<()> {
    log(format!("[API] POST /node-info {id}"));
    let client = reqwest::Client::new();
    let res = client
        .post("http://localhost:8001/node-info")
        .json(&NodeInfoRequest {
            id,
            description,
            story,
        })
        .send()
        .await?;
    let _data: NodeInfoResponse = res.json().await?;
    Ok(())
}

#[derive(Serialize)]
struct YamlRequest<'a> {
    yaml: &'a str,
}

#[derive(Deserialize)]
struct TextResponse {
    text: String,
}

#[derive(Deserialize)]
struct YamlResponse {
    yaml: String,
}

#[derive(Deserialize)]
struct ValidateResponse {
    valid: bool,
}

pub fn simulate_flow(yaml: &str) -> reqwest::Result<String> {
    let client = reqwest::blocking::Client::new();
    let res = client
        .post("http://localhost:8001/simulate/flow")
        .json(&YamlRequest { yaml })
        .send()?;
    let data: TextResponse = res.json()?;
    Ok(data.text)
}

pub fn generate_component(prompt: &str) -> reqwest::Result<String> {
    let client = reqwest::blocking::Client::new();
    let res = client
        .post("http://localhost:8001/generate/component")
        .json(&PromptRequest { text: prompt })
        .send()?;
    let data: YamlResponse = res.json()?;
    Ok(data.yaml)
}

pub fn validate_yaml(yaml: &str) -> reqwest::Result<bool> {
    let client = reqwest::blocking::Client::new();
    let res = client
        .post("http://localhost:8001/validate/yaml")
        .json(&YamlRequest { yaml })
        .send()?;
    let data: ValidateResponse = res.json()?;
    Ok(data.valid)
}

pub fn call_iot_http(path: &str) -> reqwest::Result<String> {
    push_log(format!("[HTTP] POST {}", path));
    let client = reqwest::blocking::Client::new();
    let res = client.post(&format!("http://localhost:8000{}", path)).send()?;
    Ok(res.text()?)
}

pub fn publish_mqtt(topic: &str, payload: &str) -> reqwest::Result<()> {
    push_log(format!("[MQTT] {topic}: {payload}"));
    Ok(())
}

#[derive(Serialize)]
struct CompileRequest<'a> {
    file: &'a str,
}

#[derive(Deserialize)]
struct CompileResponse {
    ok: bool,
    logs: String,
}

pub async fn compile_project(file: &str) -> reqwest::Result<(bool, String)> {
    log(format!("[API] POST /compile {file}"));
    let client = reqwest::Client::new();
    let res = client
        .post("http://localhost:8001/compile")
        .json(&CompileRequest { file })
        .send()
        .await?;
    let data: CompileResponse = res.json().await?;
    Ok((data.ok, data.logs))
}
