use std::sync::{Arc, atomic::AtomicBool, atomic::Ordering};
use studio_web::{set_api, set_previewer, compile_and_preview};
use studio_web::{GraphApi, Previewer};
use ferrum_shared_models::FerrumDsl;
use async_trait::async_trait;

struct MockApi;

#[async_trait(?Send)]
impl GraphApi for MockApi {
    async fn fetch_graph(&self) -> studio_web::api::ApiResult<FerrumDsl> { unimplemented!() }
    async fn ask_ai_team(&self, _question: &str) -> reqwest_wasm::Result<String> { unimplemented!() }
    async fn store_node_info(&self, _id: &str, _desc: Option<&str>, _story: Option<&str>) -> reqwest_wasm::Result<()> { unimplemented!() }
    async fn simulate_flow(&self, _yaml: &str) -> reqwest_wasm::Result<String> { unimplemented!() }
    async fn generate_component(&self, _prompt: &str) -> reqwest_wasm::Result<String> { unimplemented!() }
    async fn validate_yaml(&self, _yaml: &str) -> reqwest_wasm::Result<bool> { unimplemented!() }
    async fn call_iot_http(&self, _path: &str) -> reqwest_wasm::Result<String> { unimplemented!() }
    async fn publish_mqtt(&self, _topic: &str, _payload: &str) -> reqwest_wasm::Result<()> { unimplemented!() }
    async fn compile_project(&self, _file: &str) -> reqwest_wasm::Result<(bool, String)> { Ok((true, String::new())) }
    async fn compile_module(&self, _name: &str, _file: &str) -> reqwest_wasm::Result<(bool, String)> { unimplemented!() }
    async fn compile_graph(&self, _yaml: &str) -> reqwest_wasm::Result<(bool, String)> { unimplemented!() }
}

struct MockPreviewer { flag: Arc<AtomicBool> }
impl Previewer for MockPreviewer {
    fn show(&self, path: &str) {
        assert_eq!(path, "frontend/index.html");
        self.flag.store(true, Ordering::SeqCst);
    }
}

#[tokio::test]
async fn shows_preview_on_successful_compile() {
    set_api(std::sync::Arc::new(MockApi));
    let flag = Arc::new(AtomicBool::new(false));
    set_previewer(std::sync::Arc::new(MockPreviewer { flag: flag.clone() }));

    compile_and_preview("file").await.unwrap();

    assert!(flag.load(Ordering::SeqCst));
}
