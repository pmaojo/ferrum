use anyhow::Result;
use std::path::PathBuf;

use ferrum_shared_models::{DslApp, FerrumDsl};

pub fn sync(file: PathBuf, uri: String, user: String, password: String) -> Result<()> {
    use neo4rs::Graph;

    let module = ferrum_compiler::parse_yaml(&file)?;
    ferrum_compiler::validate_module(&module)?;
    let rt = tokio::runtime::Runtime::new()?;
    rt.block_on(async {
        let _graph = Graph::new(uri.clone(), user.clone(), password.clone()).await?;
        let mut dsl = FerrumDsl {
            app: DslApp {
                name: "default".to_string(),
                title: None,
                version: None,
                database: None,
                features: vec![],
                auth: None,
            },
            modules: std::collections::BTreeMap::new(),
            routes: vec![],
            pages: vec![],
            components: vec![],
            queries: vec![],
            mutations: vec![],
            jobs: vec![],
            entities: vec![],
            forms: vec![],
            validations: vec![],
            uploads: vec![],
            policies: vec![],
            resources: vec![],
            iot: vec![],
            vector_stores: vec![],
            ai_models: vec![],
        };
        dsl.modules.insert(module.name.clone(), module.into());
        ferrum_engine::sync_ast_to_graph(&dsl, &()).await?;
        Ok::<_, anyhow::Error>(())
    })?;

    println!("✅ Synced {} to {}", file.display(), uri);
    Ok(())
}

