use serde::{Deserialize, Serialize};

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

pub fn fetch_graph_blocking(question: &str) -> reqwest::Result<String> {
    let client = reqwest::blocking::Client::new();
    let res = client
        .post("http://localhost:8001/graph-rag")
        .json(&PromptRequest { text: question })
        .send()?;
    let data: GraphResponse = res.json()?;
    Ok(data.graph)
}

pub fn ask_ai_team(question: &str) -> reqwest::Result<String> {
    let client = reqwest::blocking::Client::new();
    let res = client
        .post("http://localhost:8001/ai-team")
        .json(&ChatRequest {
            messages: [Message {
                role: "user",
                content: question,
            }],
        })
        .send()?;
    let data: ChatResponse = res.json()?;
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

pub fn store_node_info(
    id: &str,
    description: Option<&str>,
    story: Option<&str>,
) -> reqwest::Result<()> {
    let client = reqwest::blocking::Client::new();
    let _ = client
        .post("http://localhost:8001/node-info")
        .json(&NodeInfoRequest {
            id,
            description,
            story,
        })
        .send()?;
    Ok(())
}
