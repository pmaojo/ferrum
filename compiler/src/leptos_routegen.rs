use anyhow::Result;
use inflector::Inflector;
use std::fs;

use ferrum_shared_models::FerrumDsl;

use crate::ProjectPaths;

/// Generate Leptos `routes.rs` based on DSL routes and pages.
pub fn generate_leptos_routes(dsl: &FerrumDsl, paths: &ProjectPaths) -> Result<()> {
    if dsl.routes.is_empty() {
        return Ok(());
    }

    let mut imports = String::new();
    for page in &dsl.pages {
        imports.push_str(&format!(
            "use crate::pages::{}::{};\n",
            page.name.to_snake_case(),
            page.name
        ));
    }

    let mut routes = String::new();
    for route in &dsl.routes {
        routes.push_str(&format!(
            "            <Route path=\"{}\" view={} />\n",
            route.path, route.to
        ));
    }

    let template = include_str!("../../templates/frontend_leptos/route.rs.tera");
    let routes_block = if routes.is_empty() {
        "<Router></Router>".to_string()
    } else {
        format!(
            "<Router>\n        <Routes>\n{routes}        </Routes>\n    </Router>",
            routes = routes
        )
    };
    let content = template.replace("<Router></Router>", &routes_block);
    let content = format!("{imports}\n{content}");

    let file = paths.root.join("frontend_leptos/src/routes.rs");
    fs::create_dir_all(file.parent().unwrap())?;
    fs::write(file, content)?;
    Ok(())
}
