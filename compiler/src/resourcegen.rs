use anyhow::Result;
use inflector::Inflector;
use std::fs;

use ferrum_shared_models::{DslResource, FerrumDsl};

use crate::ProjectPaths;

pub fn generate_resource(res: &DslResource, paths: &ProjectPaths) -> Result<()> {
    let dir = paths.backend.join("resources");
    fs::create_dir_all(&dir)?;
    let content = match res.resource_type.as_str() {
        "redis" => {
            let url = res
                .config
                .get("url")
                .cloned()
                .unwrap_or_else(|| "redis://127.0.0.1/".into());
            format!(
                "use redis::Client;\n\npub fn {}() -> Client {{\n    Client::open(\"{}\").expect(\"invalid url\")\n}}\n",
                res.name.to_snake_case(),
                url
            )
        }
        "s3" => format!(
            "use aws_sdk_s3::Client;\nuse aws_config::meta::region::RegionProviderChain;\n\npub async fn {}() -> Client {{\n    let region_provider = RegionProviderChain::default();\n    let config = aws_config::from_env().region(region_provider).load().await;\n    Client::new(&config)\n}}\n",
            res.name.to_snake_case()
        ),
        _ => format!(
            "// Resource type: {}\n// Configuration: {:?}\n",
            res.resource_type, res.config
        ),
    };
    fs::write(dir.join(format!("{}.rs", res.name.to_lowercase())), content)?;
    Ok(())
}

pub fn compile_resources(dsl: &FerrumDsl, paths: &ProjectPaths) -> Result<()> {
    for r in &dsl.resources {
        generate_resource(r, paths)?;
    }
    Ok(())
}
