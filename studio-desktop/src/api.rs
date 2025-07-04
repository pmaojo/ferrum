use bevy::prelude::*;
use bevy_tokio_tasks::TokioTasksRuntime;
use once_cell::sync::OnceCell;
use std::sync::{mpsc, Mutex};
use serde::{Deserialize, Serialize};

static LOG_SENDER: OnceCell<Mutex<mpsc::Sender<String>>> = OnceCell::new();

#[derive(Event, Clone)]
pub struct LogEvent(pub String);


pub fn push_log<S: Into<String>>(writer: &mut EventWriter<LogEvent>, msg: S) {
    let msg = msg.into();
    send_log(msg.clone());
    writer.write(LogEvent(msg));
}

fn log(writer: &mut EventWriter<LogEvent>, msg: String) {
    send_log(msg.clone());
    writer.write(LogEvent(msg));
}


fn send_log(msg: String) {
    if let Some(tx) = LOG_SENDER.get() {
        if let Ok(lock) = tx.lock() {
            let _ = lock.send(msg);
        }
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
    println!("[API] POST /graph-rag {question}");
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
    println!("[API] POST /ai-team {question}");
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


pub async fn store_node_info(
    id: &str,
    description: Option<&str>,
    story: Option<&str>,
) -> reqwest::Result<()> {
    send_log(format!("[API] POST /node-info {id}"));
    let client = reqwest::Client::new();
    client
        .post("http://localhost:8001/node-info")
        .json(&NodeInfoRequest {
            id,
            description,
            story,
        })
        .send()
        .await?
        .error_for_status()?;
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

pub async fn simulate_flow_async(yaml: &str) -> reqwest::Result<String> {
    let client = reqwest::Client::new();
    let res = client
        .post("http://localhost:8001/simulate/flow")
        .json(&YamlRequest { yaml })
        .send()
        .await?;
    let data: TextResponse = res.json().await?;
    Ok(data.text)
}

pub fn simulate_flow(
    writer: &mut EventWriter<LogEvent>,
    rt: &TokioTasksRuntime,
    yaml: &str,
) -> bevy_tokio_tasks::tokio::task::JoinHandle<reqwest::Result<String>> {
    log(writer, format!("[API] POST /simulate/flow {yaml}"));
    let yaml = yaml.to_string();
    rt.spawn_background_task(move |_| async move { simulate_flow_async(&yaml).await })
}

pub async fn generate_component_async(prompt: &str) -> reqwest::Result<String> {
    let client = reqwest::Client::new();
    let res = client
        .post("http://localhost:8001/generate/component")
        .json(&PromptRequest { text: prompt })
        .send()
        .await?;
    let data: YamlResponse = res.json().await?;
    Ok(data.yaml)
}

pub fn generate_component(
    _writer: &mut EventWriter<LogEvent>,
    rt: &TokioTasksRuntime,
    prompt: &str,
) -> bevy_tokio_tasks::tokio::task::JoinHandle<reqwest::Result<String>> {
    let prompt = prompt.to_string();
    rt.spawn_background_task(move |_| async move { generate_component_async(&prompt).await })
}

pub async fn validate_yaml_async(yaml: &str) -> reqwest::Result<bool> {
    let client = reqwest::Client::new();
    let res = client
        .post("http://localhost:8001/validate/yaml")
        .json(&YamlRequest { yaml })
        .send()
        .await?;
    let data: ValidateResponse = res.json().await?;
    Ok(data.valid)
}

pub fn validate_yaml(
    _writer: &mut EventWriter<LogEvent>,
    rt: &TokioTasksRuntime,
    yaml: &str,
) -> bevy_tokio_tasks::tokio::task::JoinHandle<reqwest::Result<bool>> {
    let yaml = yaml.to_string();
    rt.spawn_background_task(move |_| async move { validate_yaml_async(&yaml).await })
}

pub async fn call_iot_http_async(path: &str) -> reqwest::Result<String> {
    let client = reqwest::Client::new();
    let res = client
        .post(&format!("http://localhost:8001{}", path))
        .send()
        .await?;
    Ok(res.text().await?)
}

pub fn call_iot_http(
    writer: &mut EventWriter<LogEvent>,
    rt: &TokioTasksRuntime,
    path: &str,
) -> bevy_tokio_tasks::tokio::task::JoinHandle<reqwest::Result<String>> {
    push_log(writer, format!("[HTTP] POST {}", path));
    let path = path.to_string();
    rt.spawn_background_task(move |_| async move { call_iot_http_async(&path).await })
}

pub async fn publish_mqtt_async(topic: &str, payload: &str) -> reqwest::Result<()> {
    let _ = (topic, payload); // placeholder for real implementation
    Ok(())
}

pub fn publish_mqtt(
    writer: &mut EventWriter<LogEvent>,
    rt: &TokioTasksRuntime,
    topic: &str,
    payload: &str,
) -> bevy_tokio_tasks::tokio::task::JoinHandle<reqwest::Result<()>> {
    push_log(writer, format!("[MQTT] {topic}: {payload}"));
    let topic = topic.to_string();
    let payload = payload.to_string();
    rt.spawn_background_task(move |_| async move { publish_mqtt_async(&topic, &payload).await })
}

#[derive(Serialize)]
struct CompileRequest<'a> {
    file: &'a str,
}

#[derive(Serialize)]
struct ModuleCompileRequest<'a> {
    file: &'a str,
}

#[derive(Serialize)]
struct GraphCompileRequest<'a> {
    yaml: &'a str,
}

#[derive(Deserialize)]
struct CompileResponse {
    ok: bool,
    logs: String,
}

pub async fn compile_project(file: &str) -> reqwest::Result<(bool, String)> {
    send_log(format!("[API] POST /compile {file}"));
    let client = reqwest::Client::new();
    let res = client
        .post("http://localhost:8001/compile")
        .json(&CompileRequest { file })
        .send()
        .await?;
    let data: CompileResponse = res.json().await?;
    Ok((data.ok, data.logs))
}

pub async fn compile_module(name: &str, file: &str) -> reqwest::Result<(bool, String)> {
    send_log(format!("[API] POST /compile/module/{name} {file}"));
    let client = reqwest::Client::new();
    let res = client
        .post(&format!("http://localhost:8001/compile/module/{name}"))
        .json(&ModuleCompileRequest { file })
        .send()
        .await?;
    let data: CompileResponse = res.json().await?;
    Ok((data.ok, data.logs))
}

pub async fn compile_graph(yaml: &str) -> reqwest::Result<(bool, String)> {
    send_log("[API] POST /compile/graph".to_string());
    let client = reqwest::Client::new();
    let res = client
        .post("http://localhost:8001/compile/graph")
        .json(&GraphCompileRequest { yaml })
        .send()
        .await?;
    let data: CompileResponse = res.json().await?;
    Ok((data.ok, data.logs))
}
