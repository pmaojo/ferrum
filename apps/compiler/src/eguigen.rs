use anyhow::{Context, Result};
use serde::Serialize;
use std::fs;
use tera::{Context as TeraContext, Tera};

use crate::ProjectPaths;
use ferrum_shared_models::{Module, Node};

/// EGUI frontend code generator that produces native desktop UI code
/// from DSL definitions using the eframe/egui library.
pub struct EguiGenerator {
    paths: ProjectPaths,
    templates: Tera,
}

impl EguiGenerator {
    /// Create a new EGUI generator with the given project paths.
    pub fn new(paths: ProjectPaths) -> Result<Self> {
        // Initialize Tera templates for EGUI frontend
        let templates_path = paths.root.join("templates/frontend_egui/**/*");
        let templates_glob = templates_path
            .to_str()
            .context("Failed to convert templates path to string")?;

        let mut templates =
            Tera::new(templates_glob).context("Failed to initialize Tera template engine")?;
        templates.autoescape_on(vec![]);

        Ok(Self { paths, templates })
    }

    /// Generate the main EGUI application structure including main.rs and app.rs.
    pub fn generate_app(&self, _modules: &[Module]) -> Result<()> {
        let frontend_egui_dir = self.paths.root.join("frontend_egui");
        let src_dir = frontend_egui_dir.join("src");
        
        // Create directory structure
        fs::create_dir_all(&src_dir)
            .context("Failed to create frontend_egui/src directory")?;

        // Determine app name from project structure
        let app_name = self.paths.root
            .file_name()
            .and_then(|n| n.to_str())
            .unwrap_or("Ferrum App");

        // Create context for templates
        #[derive(Serialize)]
        struct AppContext<'a> {
            app_name: &'a str,
            api_base_url: &'a str,
        }

        let ctx = AppContext {
            app_name,
            api_base_url: "http://localhost:3000",
        };

        let context = TeraContext::from_serialize(&ctx)
            .context("Failed to serialize app context")?;

        // Generate Cargo.toml
        let cargo_content = self
            .templates
            .render("Cargo.toml.tera", &context)
            .context("Failed to render Cargo.toml template")?;
        fs::write(frontend_egui_dir.join("Cargo.toml"), cargo_content)
            .context("Failed to write Cargo.toml")?;

        // Generate main.rs
        let main_content = self
            .templates
            .render("main.rs.tera", &context)
            .context("Failed to render main.rs template")?;
        fs::write(src_dir.join("main.rs"), main_content)
            .context("Failed to write main.rs")?;

        // Generate app.rs
        let app_content = self
            .templates
            .render("app.rs.tera", &context)
            .context("Failed to render app.rs template")?;
        fs::write(src_dir.join("app.rs"), app_content)
            .context("Failed to write app.rs")?;

        Ok(())
    }

    /// Generate state management code with AppState struct.
    pub fn generate_state(&self, _modules: &[Module]) -> Result<()> {
        let src_dir = self.paths.root.join("frontend_egui/src");
        
        // Create empty context (state.rs template doesn't need dynamic data)
        let context = TeraContext::new();

        // Generate state.rs
        let state_content = self
            .templates
            .render("state.rs.tera", &context)
            .context("Failed to render state.rs template")?;
        fs::write(src_dir.join("state.rs"), state_content)
            .context("Failed to write state.rs")?;

        Ok(())
    }

    /// Generate navigation system with View enum and routing logic.
    pub fn generate_navigation(&self, modules: &[Module]) -> Result<()> {
        let src_dir = self.paths.root.join("frontend_egui/src");
        let api_dir = src_dir.join("api");
        
        // Create api directory
        fs::create_dir_all(&api_dir)
            .context("Failed to create api directory")?;

        // Extract routes from modules (for now, create basic routes from entities)
        #[derive(Serialize)]
        struct RouteInfo {
            view_name: String,
            display_name: String,
            path: String,
            auth_required: bool,
        }

        let mut routes = Vec::new();
        
        // Generate routes from entities in modules
        for module in modules {
            for node in &module.nodes {
                if matches!(node.node_type, ferrum_shared_models::NodeType::Entity) {
                    let view_name = crate::utils::capitalize(&node.id);
                    routes.push(RouteInfo {
                        view_name: view_name.clone(),
                        display_name: view_name,
                        path: format!("/{}", node.id.to_lowercase()),
                        auth_required: true, // Default to requiring auth for entity views
                    });
                }
            }
        }

        #[derive(Serialize)]
        struct NavigationContext {
            routes: Vec<RouteInfo>,
        }

        let ctx = NavigationContext { routes };
        let context = TeraContext::from_serialize(&ctx)
            .context("Failed to serialize navigation context")?;

        // Generate navigation.rs
        let nav_content = self
            .templates
            .render("navigation.rs.tera", &context)
            .context("Failed to render navigation.rs template")?;
        fs::write(src_dir.join("navigation.rs"), nav_content)
            .context("Failed to write navigation.rs")?;

        // Generate API client files
        let api_mod_content = self
            .templates
            .render("api/mod.rs.tera", &TeraContext::new())
            .context("Failed to render api/mod.rs template")?;
        fs::write(api_dir.join("mod.rs"), api_mod_content)
            .context("Failed to write api/mod.rs")?;

        let api_client_content = self
            .templates
            .render("api/client.rs.tera", &TeraContext::new())
            .context("Failed to render api/client.rs template")?;
        fs::write(api_dir.join("client.rs"), api_client_content)
            .context("Failed to write api/client.rs")?;

        Ok(())
    }

    /// Generate a view module for displaying an entity.
    pub fn generate_view(&self, module: &Module, node: &Node) -> Result<()> {
        let src_dir = self.paths.root.join("frontend_egui/src");
        let views_dir = src_dir.join("views");
        
        // Create views directory
        fs::create_dir_all(&views_dir)
            .context("Failed to create views directory")?;

        // Prepare view context
        let entity_name = crate::utils::capitalize(&node.id);
        let module_name = node.id.to_lowercase();
        let struct_name = format!("{}View", entity_name);
        let display_name = entity_name.clone();
        let api_path = format!("/api/{}", module.name.to_lowercase());

        // Map fields to EGUI widgets
        #[derive(Serialize)]
        struct FieldInfo {
            name: String,
            display_name: String,
            rust_type: String,
            widget_type: String,
        }

        let fields: Vec<FieldInfo> = node.input.iter().map(|field| {
            let field_type_lower = field.field_type.to_lowercase();
            let widget_type = if field_type_lower.contains("string") || field_type_lower == "str" {
                "text_edit"
            } else if field_type_lower.contains("bool") {
                "checkbox"
            } else if field_type_lower.contains("i32") 
                || field_type_lower.contains("i64")
                || field_type_lower.contains("f32")
                || field_type_lower.contains("f64")
                || field_type_lower.contains("u32")
                || field_type_lower.contains("u64")
                || field_type_lower.contains("usize")
                || field_type_lower.contains("isize") {
                "drag_value"
            } else {
                "text_edit" // Default to text edit for unknown types
            };

            FieldInfo {
                name: field.name.clone(),
                display_name: crate::utils::capitalize(&field.name),
                rust_type: field.field_type.clone(),
                widget_type: widget_type.to_string(),
            }
        }).collect();

        #[derive(Serialize)]
        struct ViewContext {
            entity_name: String,
            module_name: String,
            struct_name: String,
            display_name: String,
            api_path: String,
            fields: Vec<FieldInfo>,
        }

        let ctx = ViewContext {
            entity_name,
            module_name: module_name.clone(),
            struct_name,
            display_name,
            api_path,
            fields,
        };

        let context = TeraContext::from_serialize(&ctx)
            .context("Failed to serialize view context")?;

        // Generate view module file
        let view_content = self
            .templates
            .render("views/view.rs.tera", &context)
            .context("Failed to render view template")?;
        
        let view_file = views_dir.join(format!("{}.rs", module_name));
        fs::write(&view_file, view_content)
            .with_context(|| format!("Failed to write view file: {}", view_file.display()))?;

        Ok(())
    }

    /// Generate a form module for data input.
    pub fn generate_form(&self, _module: &Module, _node: &Node) -> Result<()> {
        // TODO: Implement in task 4
        Ok(())
    }

    /// Generate API client code for backend communication.
    pub fn generate_api_client(&self, _modules: &[Module]) -> Result<()> {
        // TODO: Implement in task 5
        Ok(())
    }

    /// Generate the views/mod.rs file that exports all view modules.
    pub fn generate_views_mod(&self, modules: &[Module]) -> Result<()> {
        let src_dir = self.paths.root.join("frontend_egui/src");
        let views_dir = src_dir.join("views");
        
        // Create views directory
        fs::create_dir_all(&views_dir)
            .context("Failed to create views directory")?;

        // Collect all entity views
        #[derive(Serialize)]
        struct ViewInfo {
            module_name: String,
            struct_name: String,
        }

        let mut views = Vec::new();
        for module in modules {
            for node in &module.nodes {
                if matches!(node.node_type, ferrum_shared_models::NodeType::Entity) {
                    let entity_name = crate::utils::capitalize(&node.id);
                    views.push(ViewInfo {
                        module_name: node.id.to_lowercase(),
                        struct_name: format!("{}View", entity_name),
                    });
                }
            }
        }

        #[derive(Serialize)]
        struct ModContext {
            views: Vec<ViewInfo>,
        }

        let ctx = ModContext { views };
        let context = TeraContext::from_serialize(&ctx)
            .context("Failed to serialize views mod context")?;

        // Generate views/mod.rs
        let mod_content = self
            .templates
            .render("views/mod.rs.tera", &context)
            .context("Failed to render views/mod.rs template")?;
        
        fs::write(views_dir.join("mod.rs"), mod_content)
            .context("Failed to write views/mod.rs")?;

        Ok(())
    }
}
