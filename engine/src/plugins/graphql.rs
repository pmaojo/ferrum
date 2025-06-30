use anyhow::Result;
use std::fs;
use std::path::Path;

use super::Plugin;

/// Plugin that provides basic GraphQL support.
pub struct GraphQLPlugin;

impl Plugin for GraphQLPlugin {
    fn name(&self) -> &'static str { "graphql" }

    fn on_init(&self) -> Result<()> {
        copy_schema_template("backend/src/graphql_schema.rs")
    }

    fn on_compile(&self) -> Result<()> {
        // Ensure schema exists each compile
        copy_schema_template("backend/src/graphql_schema.rs")
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
