use anyhow::{Context, Result};
use std::fs;
use std::path::{Path, PathBuf};
use tera::{Context as TeraContext, Tera};

use crate::ast::{Module, Node, NodeType};

pub struct Generator {
    templates: Tera,
    output_dir: PathBuf,
}

impl Generator {
    pub fn new<P: AsRef<Path>>(templates_dir: P, output_dir: P) -> Result<Self> {
        let templates_path = templates_dir.as_ref().join("**/*");
        let templates_glob = templates_path
            .to_str()
            .context("Failed to convert templates path to string")?;

        let mut templates = Tera::new(templates_glob)
            .context("Failed to initialize Tera template engine")?;
        templates.autoescape_on(vec![]);

        Ok(Self {
            templates,
            output_dir: output_dir.as_ref().to_path_buf(),
        })
    }

    pub fn generate(&self, module: &Module) -> Result<()> {
        for node in &module.nodes {
            self.generate_node(module, node)?;
        }

        // Run post-processing tasks
        self.run_post_processing()
    }

    fn generate_node(&self, module: &Module, node: &Node) -> Result<()> {
        match node.node_type {
            NodeType::UseCase => self.generate_usecase(module, node),
            NodeType::Adapter => self.generate_adapter(module, node),
            NodeType::Port => self.generate_port(module, node),
            NodeType::Entity => self.generate_entity(module, node),
        }
    }

    fn generate_usecase(&self, module: &Module, node: &Node) -> Result<()> {
        let mut context = TeraContext::new();
        context.insert("module", module);
        context.insert("node", node);
        // Add module name directly to context for templates
        context.insert("module_name", &module.name);

        // Generate handler
        let handler_content = self.templates.render("backend/handler.tera", &context)
            .context("Failed to render handler template")?;
        let handler_path = self.output_dir.join("backend/handlers")
            .join(format!("{}.rs", module.name));
        self.write_file(&handler_path, &handler_content)?;

        // Generate route
        let route_content = self.templates.render("backend/route.tera", &context)
            .context("Failed to render route template")?;
        let route_path = self.output_dir.join("backend/routes")
            .join(format!("{}.rs", module.name));
        self.write_file(&route_path, &route_content)?;

        // Generate frontend hook
        let hook_content = self.templates.render("frontend/hook.tera", &context)
            .context("Failed to render hook template")?;
        let hook_path = self.output_dir.join("frontend/src/hooks")
            .join(format!("use{}.ts", capitalize(&node.id)));
        self.write_file(&hook_path, &hook_content)?;

        // Generate frontend component
        let component_content = self.templates.render("frontend/component.tera", &context)
            .context("Failed to render component template")?;
        let component_path = self.output_dir.join("frontend/src/components")
            .join(format!("{}.tsx", capitalize(&node.id)));
        self.write_file(&component_path, &component_content)?;

        Ok(())
    }

    fn generate_adapter(&self, module: &Module, node: &Node) -> Result<()> {
        let mut context = TeraContext::new();
        context.insert("module", module);
        context.insert("node", node);
        context.insert("module_name", &module.name);

        let adapter_content = self.templates.render("backend/adapter.tera", &context)
            .context("Failed to render adapter template")?;
        let adapter_path = self.output_dir.join("backend/db")
            .join(format!("{}.rs", module.name));
        self.write_file(&adapter_path, &adapter_content)?;

        Ok(())
    }

    fn generate_port(&self, module: &Module, node: &Node) -> Result<()> {
        let mut context = TeraContext::new();
        context.insert("module", module);
        context.insert("node", node);
        context.insert("module_name", &module.name);

        let port_content = self.templates.render("backend/port.tera", &context)
            .context("Failed to render port template")?;
        let port_path = self.output_dir.join("backend/ports.rs");
        
        // Append to ports file or create if it doesn't exist
        let existing_content = if port_path.exists() {
            fs::read_to_string(&port_path).unwrap_or_default()
        } else {
            String::new()
        };

        let updated_content = if existing_content.is_empty() {
            port_content
        } else {
            format!("{}{}", existing_content, port_content)
        };

        self.write_file(&port_path, &updated_content)?;

        Ok(())
    }

    fn generate_entity(&self, module: &Module, node: &Node) -> Result<()> {
        let mut context = TeraContext::new();
        context.insert("module", module);
        context.insert("node", node);
        context.insert("module_name", &module.name);

        // Generate Rust model
        let model_content = self.templates.render("shared-models/model.tera", &context)
            .context("Failed to render model template")?;
        let model_path = self.output_dir.join("shared-models")
            .join(format!("{}.rs", node.id.to_lowercase()));
        self.write_file(&model_path, &model_content)?;

        // Generate TypeScript schema
        let schema_content = self.templates.render("frontend/schema.tera", &context)
            .context("Failed to render schema template")?;
        let schema_path = self.output_dir.join("frontend/src/schemas")
            .join(format!("{}.ts", node.id.to_lowercase()));
        self.write_file(&schema_path, &schema_content)?;

        Ok(())
    }

    fn write_file<P: AsRef<Path>>(&self, path: P, content: &str) -> Result<()> {
        let path = path.as_ref();
        if let Some(parent) = path.parent() {
            fs::create_dir_all(parent)
                .with_context(|| format!("Failed to create directory: {}", parent.display()))?;
        }

        fs::write(path, content)
            .with_context(|| format!("Failed to write file: {}", path.display()))?;

        Ok(())
    }

    fn run_post_processing(&self) -> Result<()> {
        // This would run typeshare, cargo fmt, prettier, etc.
        // For now, we'll just return Ok as a placeholder
        Ok(())
    }
}

// Helper function to capitalize first letter of a string
fn capitalize(s: &str) -> String {
    let mut chars = s.chars();
    match chars.next() {
        None => String::new(),
        Some(first) => first.to_uppercase().collect::<String>() + chars.as_str(),
    }
}
