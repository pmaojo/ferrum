use studio_web::{HttpGraphApi, GraphApi};
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
