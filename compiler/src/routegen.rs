use anyhow::Result;
use std::fs;

use ferrum_shared_models::FerrumDsl;

use crate::querygen::ProjectPaths;

/// Generate frontend routes.tsx based on DSL routes and pages.
pub fn generate_routes(dsl: &FerrumDsl, paths: &ProjectPaths) -> Result<()> {
    if dsl.routes.is_empty() {
        return Ok(());
    }
    let mut imports = String::new();
    for page in &dsl.pages {
        imports.push_str(&format!("import {{ {} }} from './pages/{}';\n", page.name, page.component.trim_end_matches(".tsx")));
    }
    let mut routes_arr = String::from("const routes = [\n");
    for route in &dsl.routes {
        routes_arr.push_str(&format!(
            "  {{ path: '{}', element: <{} />, authRequired: {} }},\n",
            route.path,
            route.to,
            route.auth_required
        ));
    }
    routes_arr.push_str("] as const;\n\nexport default routes;\n");
    let content = format!("{imports}\n{routes_arr}");
    let file = paths.frontend.join("routes.tsx");
    fs::create_dir_all(file.parent().unwrap())?;
    fs::write(file, content)?;
    Ok(())
}
