use anyhow::Result;
use inflector::Inflector;
use std::fs;

use ferrum_shared_models::FerrumDsl;

use crate::ProjectPaths;

/// Generate basic Leptos pages based on the DSL `pages` section.
pub fn generate_leptos_pages(dsl: &FerrumDsl, paths: &ProjectPaths) -> Result<()> {
    if dsl.pages.is_empty() {
        return Ok(());
    }

    for page in &dsl.pages {
        let file_name = format!("{}.rs", page.name.to_snake_case());
        let file = paths
            .root
            .join("frontend_leptos/src/pages")
            .join(file_name);
        fs::create_dir_all(file.parent().unwrap())?;
        let content = format!(
            "use leptos::*;\n\n#[component]\npub fn {name}() -> impl IntoView {{\n    view! {{ <h1>Bienvenido a {name}</h1> }}\n}}\n",
            name = page.name
        );
        fs::write(file, content)?;
    }
    Ok(())
}

