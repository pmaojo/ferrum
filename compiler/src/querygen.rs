use anyhow::Result;
use inflector::Inflector;
use std::fs;
use std::path::{Path, PathBuf};

use ferrum_shared_models::DslQuery;
use ferrum_shared_models::FerrumDsl;

#[derive(Debug, Clone)]
pub struct ProjectPaths {
    pub root: PathBuf,
    pub backend: PathBuf,
    pub frontend: PathBuf,
}

impl ProjectPaths {
    pub fn new<P: AsRef<Path>>(root: P) -> Self {
        let root = root.as_ref().to_path_buf();
        Self {
            backend: root.join("backend"),
            frontend: root.join("frontend"),
            root,
        }
    }
}

/// Capitalize the first letter of a string.
pub fn capitalize(s: &str) -> String {
    let mut chars = s.chars();
    match chars.next() {
        None => String::new(),
        Some(first) => first.to_uppercase().collect::<String>() + chars.as_str(),
    }
}

/// Generate source files for a DSL query entry.
pub fn generate_query(query: &DslQuery, paths: &ProjectPaths) -> Result<()> {
    let func_name = query.name.to_snake_case();
    let hook_name = query.name.to_pascal_case();
    let backend_dir = paths.backend.join("queries");
    let frontend_dir = paths.frontend.join("hooks");
    fs::create_dir_all(&backend_dir)?;
    fs::create_dir_all(&frontend_dir)?;

    let mut imports = String::new();
    for ent in &query.entities {
        imports.push_str(&format!(
            "use crate::domain::{}::{};\n",
            ent.to_snake_case(),
            ent
        ));
    }
    let ret_ty = query
        .entities
        .first()
        .cloned()
        .unwrap_or_else(|| "serde_json::Value".into());

    let rust_content = format!(
        "{imports}use axum::{{Json, extract::State}};\nuse std::sync::Arc;\nuse crate::AppState;\n\npub async fn {func_name}(State(_state): State<Arc<AppState>>) -> Json<Vec<{ret_ty}>> {{\n    // ⛳️ AI_FILL[query_logic] --context=query:{orig}\n    Json(vec![])\n}}\n",
        imports = imports,
        func_name = func_name,
        ret_ty = ret_ty,
        orig = query.name,
    );
    fs::write(backend_dir.join(format!("{}.rs", func_name)), rust_content)?;

    let ts_import = query
        .entities
        .first()
        .map(|e| format!("import {{ {e} }} from '../types';\n"))
        .unwrap_or_default();
    let ts_ret = query
        .entities
        .first()
        .cloned()
        .unwrap_or_else(|| "any".into());
    let ts_content = format!(
        "import {{ useEffect, useState }} from 'react';\n{ts_import}\nexport function use{hook_name}() {{\n  const [data, setData] = useState<{ts_ret}[]>([]);\n  const [loading, setLoading] = useState(true);\n\n  useEffect(() => {{\n    fetch('/api/queries/{orig}')\n      .then(res => res.json())\n      .then(setData)\n      .finally(() => setLoading(false));\n  }}, []);\n\n  return {{ data, loading }};\n}}\n",
        ts_import = ts_import,
        hook_name = hook_name,
        ts_ret = ts_ret,
        orig = query.name
    );
    fs::write(frontend_dir.join(format!("use{hook_name}.ts")), ts_content)?;

    Ok(())
}

/// Compile all sections of the DSL that map to direct code generation.
///
/// Currently this only handles `queries`, generating a Rust handler and a
/// React hook for each entry. Other sections will be supported in the future.
pub fn compile_dsl(dsl: &FerrumDsl, paths: &ProjectPaths) -> Result<()> {
    for query in &dsl.queries {
        generate_query(query, paths)?;
    }
    // Mutations
    crate::mutationgen::compile_mutations(dsl, paths)?;
    // Routes
    crate::routegen::generate_routes(dsl, paths)?;
    // Authentication
    crate::authgen::generate_auth(dsl, paths)?;
    // Jobs
    crate::jobgen::compile_jobs(dsl, paths)?;
    // Policies
    crate::policygen::compile_policies(dsl, paths)?;
    // Resources
    crate::resourcegen::compile_resources(dsl, paths)?;
    // Components
    crate::componentgen::compile_components(dsl, paths)?;
    Ok(())
}

#[cfg(test)]
mod tests {
    use super::*;
    use tempfile::tempdir;

    #[test]
    fn generate_query_creates_files() {
        let dir = tempdir().unwrap();
        let paths = ProjectPaths::new(dir.path());
        let query = DslQuery {
            name: "getPosts".into(),
            handler: "./backend/queries/getPosts.rs".into(),
            entities: vec!["Post".into()],
            cache: None,
        };
        generate_query(&query, &paths).unwrap();
        assert!(dir.path().join("backend/queries/get_posts.rs").exists());
        assert!(dir.path().join("frontend/hooks/useGetPosts.ts").exists());
    }
}
