use std::sync::{Arc, Mutex};
use async_trait::async_trait;
use ferrum_shared_models::FerrumDsl;
use studio_web::{
    compile_project_and_preview, set_api, set_preview_opener, GraphApi,
    ui::preview::PreviewOpener,
};
use studio_web::api::ApiResult;

struct MockApi;

#[async_trait(?Send)]
impl GraphApi for MockApi {
    async fn fetch_graph(&self) -> ApiResult<FerrumDsl> {
        unreachable!()
    }
    async fn ask_ai_team(&self, _question: &str) -> reqwest_wasm::Result<String> { unreachable!() }
    async fn store_node_info(&self, _id: &str, _d: Option<&str>, _s: Option<&str>) -> reqwest_wasm::Result<()> { unreachable!() }
    async fn simulate_flow(&self, _yaml: &str) -> reqwest_wasm::Result<String> { unreachable!() }
    async fn generate_component(&self, _prompt: &str) -> reqwest_wasm::Result<String> { unreachable!() }
    async fn validate_yaml(&self, _yaml: &str) -> reqwest_wasm::Result<bool> { unreachable!() }
    async fn call_iot_http(&self, _path: &str) -> reqwest_wasm::Result<String> { unreachable!() }
    async fn publish_mqtt(&self, _t: &str, _p: &str) -> reqwest_wasm::Result<()> { unreachable!() }
    async fn compile_project(&self, _file: &str) -> reqwest_wasm::Result<(bool, String)> {
        Ok((true, String::new()))
    }
    async fn compile_module(&self, _: &str, _: &str) -> reqwest_wasm::Result<(bool, String)> { unreachable!() }
    async fn compile_graph(&self, _: &str) -> reqwest_wasm::Result<(bool, String)> { unreachable!() }
}

#[derive(Clone)]
struct TestOpener(Arc<Mutex<Vec<String>>>);

impl PreviewOpener for TestOpener {
    fn open(&self, url: &str) {
        self.0.lock().unwrap().push(url.to_string());
    }
}

#[tokio::test]
async fn compile_preview_opens_index() {
    let storage = Arc::new(Mutex::new(Vec::new()));
    let opener = TestOpener(storage.clone());
    set_preview_opener(Box::new(opener));
    set_api(Box::new(MockApi));

    compile_project_and_preview("file").await.unwrap();

    let calls = storage.lock().unwrap();
    assert_eq!(calls.len(), 1);
    assert!(calls[0].ends_with("/frontend/index.html"));
}
