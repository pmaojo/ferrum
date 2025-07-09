use studio_web::{GraphApi, HttpGraphApi};
use mockito::Server;
use serde_json::json;

#[tokio::test]
async fn fetch_graph_returns_dsl() {
    let mut server = Server::new_async().await;
    let graph_yaml = "---\napp:\n  name: demo";
    let _m = server
        .mock("POST", "/graph-rag")
        .with_body(json!({"graph": graph_yaml}).to_string())
        .create_async()
        .await;

    let api = HttpGraphApi::new(server.url());
    let dsl = api.fetch_graph().await.unwrap();
    assert_eq!(dsl.app.name, "demo");
}

#[tokio::test]
async fn ask_ai_team_returns_message() {
    let mut server = Server::new_async().await;
    let _m = server
        .mock("POST", "/ai-team")
        .with_body(json!({"message": "hi"}).to_string())
        .create_async()
        .await;

    let api = HttpGraphApi::new(server.url());
    let msg = api.ask_ai_team("hello").await.unwrap();
    assert_eq!(msg, "hi");
}

#[tokio::test]
async fn fetch_graph_invalid_yaml_returns_err() {
    let mut server = Server::new_async().await;
    let _m = server
        .mock("POST", "/graph-rag")
        .with_body(json!({"graph": "invalid"}).to_string())
        .create_async()
        .await;

    let api = HttpGraphApi::new(server.url());
    assert!(api.fetch_graph().await.is_err());
}

#[tokio::test]
async fn fetch_graph_missing_field_returns_err() {
    let mut server = Server::new_async().await;
    let _m = server
        .mock("POST", "/graph-rag")
        .with_body(json!({}).to_string())
        .create_async()
        .await;

    let api = HttpGraphApi::new(server.url());
    assert!(api.fetch_graph().await.is_err());
}
