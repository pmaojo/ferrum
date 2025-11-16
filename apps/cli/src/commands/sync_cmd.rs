use anyhow::Result;
use std::path::PathBuf;

pub fn sync(file: PathBuf, uri: String, user: String, password: String) -> Result<()> {
    use neo4rs::Graph;

    let module = ferrum_compiler::parse_yaml(&file)?;
    ferrum_compiler::validate_module(&module)?;
    let rt = tokio::runtime::Runtime::new()?;
    rt.block_on(async {
        let graph = Graph::new(uri.clone(), user.clone(), password.clone())?;
        ferrum_engine::sync_ast_to_graph(&module, &graph).await?;
        Ok::<_, anyhow::Error>(())
    })?;

    println!("✅ Synced {} to {}", file.display(), uri);
    Ok(())
}

