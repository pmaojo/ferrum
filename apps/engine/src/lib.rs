use ferrum_shared_models::*;

pub mod plugins;

pub fn sync_ast_to_graph(
    _module: &FerrumDsl,
    _graph: &(),
) -> std::future::Ready<Result<(), anyhow::Error>> {
    std::future::ready(Ok(()))
}

// Engine functionality will be implemented here
pub fn hello_engine() -> String {
    "Hello from Ferrum Engine!".to_string()
}
