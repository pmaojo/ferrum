use std::sync::{Arc, atomic::{AtomicUsize, Ordering}};

use async_trait::async_trait;
use ferrum_shared_models::{Node, NodeType};
use studio_web::{viewer::{edges, layout, simulate, store_info}, graph::GraphData, GraphApi};
use ferrum_shared_models::FerrumDsl;

struct MockApi {
    sim: AtomicUsize,
    store: AtomicUsize,
}

#[async_trait(?Send)]
impl GraphApi for MockApi {
    async fn fetch_graph(&self) -> studio_web::api::ApiResult<FerrumDsl> { unimplemented!() }
    async fn ask_ai_team(&self, _question: &str) -> reqwest_wasm::Result<String> { unimplemented!() }
    async fn store_node_info(&self, _id: &str, _d: Option<&str>, _s: Option<&str>) -> reqwest_wasm::Result<()> {
        self.store.fetch_add(1, Ordering::SeqCst);
        Ok(())
    }
    async fn simulate_flow(&self, _yaml: &str) -> reqwest_wasm::Result<String> {
        self.sim.fetch_add(1, Ordering::SeqCst);
        Ok(String::new())
    }
    async fn generate_component(&self, _prompt: &str) -> reqwest_wasm::Result<String> { unimplemented!() }
    async fn validate_yaml(&self, _yaml: &str) -> reqwest_wasm::Result<bool> { unimplemented!() }
    async fn call_iot_http(&self, _path: &str) -> reqwest_wasm::Result<String> { unimplemented!() }
    async fn publish_mqtt(&self, _topic: &str, _payload: &str) -> reqwest_wasm::Result<()> { unimplemented!() }
    async fn compile_project(&self, _file: &str) -> reqwest_wasm::Result<(bool, String)> { unimplemented!() }
    async fn compile_module(&self, _name: &str, _file: &str) -> reqwest_wasm::Result<(bool, String)> { unimplemented!() }
    async fn compile_graph(&self, _yaml: &str) -> reqwest_wasm::Result<(bool, String)> { unimplemented!() }
}

fn node(id: &str) -> Node {
    Node {
        id: id.into(),
        node_type: NodeType::Component,
        doc: None,
        description: None,
        story: None,
        input: Vec::new(),
        output: None,
        depends_on: Vec::new(),
        implements: None,
        view: None,
        schema: None,
        api_name: None,
        ref_node: None,
    }
}

#[test]
fn computes_edges() {
    let mut a = node("a");
    a.depends_on.push("b".into());
    let data = GraphData { nodes: vec![a, node("b")] };
    let e = edges(&data);
    assert_eq!(e, vec![("a".into(), "b".into())]);
}

#[test]
fn layout_provides_positions() {
    let data = GraphData { nodes: vec![node("a"), node("b")] };
    let l = layout(&data);
    assert_eq!(l.len(), 2);
    assert!(l.get("a").is_some());
}

#[tokio::test]
async fn actions_delegate_to_api() {
    let api = Arc::new(MockApi { sim: AtomicUsize::new(0), store: AtomicUsize::new(0) });
    let n = node("a");
    simulate(api.clone(), serde_yaml::to_string(&n).unwrap()).await;
    store_info(api.clone(), n.clone()).await;
    assert_eq!(api.sim.load(Ordering::SeqCst), 1);
    assert_eq!(api.store.load(Ordering::SeqCst), 1);
}
