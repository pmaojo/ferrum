use anyhow::Result;
use std::fs;
use std::fs::OpenOptions;
use std::io::Write;
use std::path::Path;

use ferrum_shared_models::FerrumDsl;

use super::Plugin;

/// Plugin that provides basic GraphQL support.
pub struct GraphQLPlugin;

impl Plugin for GraphQLPlugin {
    fn name(&self) -> &'static str {
        "graphql"
    }

    fn on_init(&self) -> Result<()> {
        copy_schema_template("backend/src/graphql_schema.rs")?;
        ensure_dependencies()
    }

    fn on_compile(&self) -> Result<()> {
        // Ensure schema exists each compile
        copy_schema_template("backend/src/graphql_schema.rs")?;
        ensure_dependencies()
    }

    fn extend_dsl(&self, dsl: &mut FerrumDsl) -> Result<()> {
        if !dsl.app.features.contains(&"graphql".to_string()) {
            dsl.app.features.push("graphql".to_string());
        }
        Ok(())
    }
}

fn copy_schema_template<P: AsRef<Path>>(dest: P) -> Result<()> {
    let contents = include_str!("../../../templates/graphql/schema.rs");
    if let Some(parent) = dest.as_ref().parent() {
        fs::create_dir_all(parent)?;
    }
    fs::write(dest, contents)?;
    Ok(())
}

fn ensure_dependencies() -> Result<()> {
    ensure_dep("async-graphql", "7")
}

fn ensure_dep(dep: &str, version: &str) -> Result<()> {
    let path = Path::new("backend/Cargo.toml");
    if !path.exists() {
        return Ok(());
    }
    let contents = fs::read_to_string(path)?;
    if !contents.contains(dep) {
        let mut f = OpenOptions::new().append(true).open(path)?;
        writeln!(f, "{dep} = \"{version}\"")?;
    }
    Ok(())
}
