use studio_web::{HttpGraphApi, GraphApi};
use studio_web::api::ApiError;

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
async fn fetch_graph_invalid_yaml_errors() {
    let mut server = Server::new_async().await;
    let _m = server
        .mock("POST", "/graph-rag")
        .with_body(json!({"graph": "invalid"}).to_string())
        .create_async()
        .await;

    let api = HttpGraphApi::new(server.url());
    let err = api.fetch_graph().await.unwrap_err();
    assert!(matches!(err, ApiError::Parse(_)));
}

#[tokio::test]
async fn fetch_graph_missing_field_errors() {
    let mut server = Server::new_async().await;
    let _m = server
        .mock("POST", "/graph-rag")
        .with_body(json!({"foo": "bar"}).to_string())
        .create_async()
        .await;

    let api = HttpGraphApi::new(server.url());
    let err = api.fetch_graph().await.unwrap_err();
    assert!(matches!(err, ApiError::MissingGraph));
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
async fn store_node_info_sends_data() {
    let mut server = Server::new_async().await;
    let _m = server
        .mock("POST", "/node-info")
        .with_status(200)
        .create_async()
        .await;

    let api = HttpGraphApi::new(server.url());
    api
        .store_node_info("a", Some("desc"), Some("story"))
        .await
        .unwrap();
}

#[tokio::test]
async fn simulate_flow_returns_text() {
    let mut server = Server::new_async().await;
    let _m = server
        .mock("POST", "/simulate/flow")
        .with_body(json!({"text": "ok"}).to_string())
        .create_async()
        .await;

    let api = HttpGraphApi::new(server.url());
    let text = api.simulate_flow("yaml").await.unwrap();
    assert_eq!(text, "ok");
}

#[tokio::test]
async fn generate_component_returns_yaml() {
    let mut server = Server::new_async().await;
    let _m = server
        .mock("POST", "/generate/component")
        .with_body(json!({"yaml": "component"}).to_string())
        .create_async()
        .await;

    let api = HttpGraphApi::new(server.url());
    let yaml = api.generate_component("prompt").await.unwrap();
    assert_eq!(yaml, "component");
}

#[tokio::test]
async fn validate_yaml_returns_bool() {
    let mut server = Server::new_async().await;
    let _m = server
        .mock("POST", "/validate/yaml")
        .with_body(json!({"valid": true}).to_string())
        .create_async()
        .await;

    let api = HttpGraphApi::new(server.url());
    let valid = api.validate_yaml("yaml").await.unwrap();
    assert!(valid);
}

#[tokio::test]
async fn call_iot_http_returns_string() {
    let mut server = Server::new_async().await;
    let _m = server
        .mock("POST", "/iot")
        .with_body("pong")
        .create_async()
        .await;

    let api = HttpGraphApi::new(server.url());
    let res = api.call_iot_http("/iot").await.unwrap();
    assert_eq!(res, "pong");
}

#[tokio::test]
async fn compile_project_returns_tuple() {
    let mut server = Server::new_async().await;
    let _m = server
        .mock("POST", "/compile")
        .with_body(json!({"ok": true, "logs": "done"}).to_string())
        .create_async()
        .await;

    let api = HttpGraphApi::new(server.url());
    let (ok, logs) = api.compile_project("file").await.unwrap();
    assert!(ok);
    assert_eq!(logs, "done");
}

#[tokio::test]
async fn compile_module_returns_tuple() {
    let mut server = Server::new_async().await;
    let _m = server
        .mock("POST", "/compile/module/foo")
        .with_body(json!({"ok": true, "logs": "ok"}).to_string())
        .create_async()
        .await;

    let api = HttpGraphApi::new(server.url());
    let (ok, logs) = api.compile_module("foo", "file").await.unwrap();
    assert!(ok);
    assert_eq!(logs, "ok");
}

#[tokio::test]
async fn compile_graph_returns_tuple() {
    let mut server = Server::new_async().await;
    let _m = server
        .mock("POST", "/compile/graph")
        .with_body(json!({"ok": false, "logs": "fail"}).to_string())
        .create_async()
        .await;

    let api = HttpGraphApi::new(server.url());
    let (ok, logs) = api.compile_graph("yaml").await.unwrap();
    assert!(!ok);
    assert_eq!(logs, "fail");
}
