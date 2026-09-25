use anyhow::Result;
use std::fs;

use ferrum_shared_models::FerrumDsl;

use crate::utils::write_file;
use crate::ProjectPaths;

/// The `App.tsx` produced by `ferrum init`. It is a throwaway placeholder, so
/// the router shell may replace it. Any other content is treated as user code
/// and left untouched.
const INIT_APP_PLACEHOLDER: &str =
    "export default function App() {\n  return <h1>Ferrum app ready!</h1>;\n}\n";

/// Reduce a page reference (`HomePage`, `HomePage.tsx`, `pages/HomePage.tsx`)
/// to the bare component symbol `HomePage`.
fn component_symbol(target: &str) -> String {
    let last = target.rsplit('/').next().unwrap_or(target);
    last.trim_end_matches(".tsx").trim().to_string()
}

/// Generate the frontend router, placeholder pages and the app shell from the
/// DSL `routes:`/`pages:` sections, plus an Axum route table for the backend.
pub fn generate_routes(dsl: &FerrumDsl, paths: &ProjectPaths) -> Result<()> {
    if dsl.routes.is_empty() {
        return Ok(());
    }

    let src = paths.frontend.join("src");
    let pages_dir = src.join("pages");

    // Route targets must be imported by routes.tsx, so every one of them needs
    // a module on disk or the generated bundle fails to resolve the import.
    let mut route_targets: Vec<String> = Vec::new();
    for route in &dsl.routes {
        let symbol = component_symbol(&route.to);
        if !symbol.is_empty() && !route_targets.contains(&symbol) {
            route_targets.push(symbol);
        }
    }

    // Pages declared in the DSL but not referenced by a route still get a
    // placeholder so they can be imported by hand.
    let mut page_targets = route_targets.clone();
    for page in &dsl.pages {
        let symbol = component_symbol(&page.component);
        if !symbol.is_empty() && !page_targets.contains(&symbol) {
            page_targets.push(symbol);
        }
    }

    // Placeholders are created only when missing, so hand-written page bodies
    // survive recompiles.
    for symbol in &page_targets {
        let page_file = pages_dir.join(format!("{symbol}.tsx"));
        if !page_file.exists() {
            let body = format!(
                r#"// Generated placeholder for the `{symbol}` page.
// Replace the body below — `ferrum compile` will not overwrite this file.
export default function {symbol}() {{
  return (
    <main className="page">
      <h1>{symbol}</h1>
    </main>
  );
}}
"#
            );
            write_file(&page_file, &body)?;
        }
    }

    // routes.tsx — real react-router objects. `authRequired`/`policy` are
    // carried in `handle`, which react-router reserves for arbitrary route
    // metadata, so a guard component can read them via `useMatches()`.
    let mut content = String::from("import type { RouteObject } from 'react-router-dom';\n");
    for symbol in &route_targets {
        content.push_str(&format!("import {symbol} from './pages/{symbol}';\n"));
    }
    content.push_str(
        "\n/**\n * Generated from the `routes:`/`pages:` sections of grafo.yaml.\n * \
         `handle.authRequired` and `handle.policy` are metadata for your own guard\n * \
         component; wrap `element` in it if you need route protection.\n */\n",
    );
    content.push_str("export const routes: RouteObject[] = [\n");
    for route in &dsl.routes {
        let symbol = component_symbol(&route.to);
        let handle = match &route.policy {
            Some(policy) => format!(
                "{{ authRequired: {}, policy: '{}' }}",
                route.auth_required, policy
            ),
            None => format!("{{ authRequired: {} }}", route.auth_required),
        };
        content.push_str(&format!(
            "  {{\n    path: '{}',\n    element: <{} />,\n    handle: {},\n  }},\n",
            route.path, symbol, handle
        ));
    }
    content.push_str("];\n\nexport default routes;\n");
    write_file(src.join("routes.tsx"), &content)?;

    // App shell — only replaces the untouched `ferrum init` placeholder.
    let app_file = src.join("App.tsx");
    let app_is_placeholder = fs::read_to_string(&app_file)
        .map(|current| current == INIT_APP_PLACEHOLDER)
        .unwrap_or(true);
    if app_is_placeholder {
        let app = "import { RouterProvider, createBrowserRouter } from 'react-router-dom';\n\
                   import routes from './routes';\n\n\
                   const router = createBrowserRouter(routes);\n\n\
                   export default function App() {\n\
                   \x20 return <RouterProvider router={router} />;\n\
                   }\n";
        write_file(&app_file, app)?;
    }

    // Also generate a simple backend routes list for Axum
    let mut backend = String::from("pub const ROUTES: &[(&str, &str)] = &[\n");
    for route in &dsl.routes {
        backend.push_str(&format!("    (\"{}\", \"{}\"),\n", route.name, route.path));
    }
    backend.push_str("]\n");
    let backend_file = paths.backend.join("src").join("routes.rs");
    fs::create_dir_all(backend_file.parent().unwrap())?;
    fs::write(backend_file, backend)?;

    Ok(())
}

#[cfg(test)]
mod tests {
    use super::*;
    use ferrum_shared_models::{DslApp, DslAppPage, DslRoute};

    fn dsl_with_routes() -> FerrumDsl {
        FerrumDsl {
            app: DslApp {
                name: "demo".into(),
                title: None,
                version: None,
                database: None,
                features: vec![],
                auth: None,
            },
            modules: Default::default(),
            routes: vec![
                DslRoute {
                    name: "home".into(),
                    path: "/".into(),
                    to: "HomePage".into(),
                    auth_required: false,
                    policy: None,
                },
                DslRoute {
                    name: "admin".into(),
                    path: "/admin".into(),
                    to: "pages/AdminPage.tsx".into(),
                    auth_required: true,
                    policy: Some("isAdmin".into()),
                },
            ],
            pages: vec![DslAppPage {
                name: "HomePage".into(),
                component: "HomePage.tsx".into(),
            }],
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
        }
    }

    #[test]
    fn writes_router_pages_and_app_shell() {
        let dir = tempfile::tempdir().unwrap();
        let paths = ProjectPaths::new(dir.path());
        generate_routes(&dsl_with_routes(), &paths).unwrap();

        let routes = fs::read_to_string(dir.path().join("frontend/src/routes.tsx")).unwrap();
        assert!(routes.contains("import HomePage from './pages/HomePage';"));
        assert!(routes.contains("import AdminPage from './pages/AdminPage';"));
        assert!(routes.contains("path: '/admin'"));
        assert!(routes.contains("policy: 'isAdmin'"));
        assert!(routes.contains("RouteObject[]"));

        assert!(dir.path().join("frontend/src/pages/HomePage.tsx").exists());
        assert!(dir.path().join("frontend/src/pages/AdminPage.tsx").exists());
        assert!(dir.path().join("frontend/src/App.tsx").exists());
    }

    #[test]
    fn preserves_hand_written_pages_and_app() {
        let dir = tempfile::tempdir().unwrap();
        let paths = ProjectPaths::new(dir.path());
        let pages = dir.path().join("frontend/src/pages");
        fs::create_dir_all(&pages).unwrap();
        fs::write(pages.join("HomePage.tsx"), "export default () => <b>mine</b>;\n").unwrap();
        let app = dir.path().join("frontend/src/App.tsx");
        fs::write(&app, "export default function App() { return <i>custom</i>; }\n").unwrap();

        generate_routes(&dsl_with_routes(), &paths).unwrap();

        assert_eq!(
            fs::read_to_string(pages.join("HomePage.tsx")).unwrap(),
            "export default () => <b>mine</b>;\n"
        );
        assert_eq!(
            fs::read_to_string(&app).unwrap(),
            "export default function App() { return <i>custom</i>; }\n"
        );
    }
}
