use serde::{Deserialize, Serialize};

#[derive(Serialize)]
struct PromptRequest<'a> {
    text: &'a str,
}

#[derive(Deserialize)]
struct GraphResponse {
    graph: String,
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
