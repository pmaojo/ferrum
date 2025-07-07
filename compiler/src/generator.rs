use anyhow::{Context, Result};
use std::fs;
use std::path::{Path, PathBuf};
use tera::{Context as TeraContext, Tera};

use crate::template_context::*;
use ferrum_shared_models::{Module, Node, NodeType};
use crate::node_generator::{
    AdapterGenerator, ComponentGenerator, EntityGenerator, FormGenerator,
    HookGenerator, NodeGenerator, PortGenerator, SchemaGenerator, UploadGenerator,
    UsecaseGenerator, ValidationGenerator, GeneratorContext,
};

/// Code generator that materializes a graph of nodes into Rust and
/// TypeScript sources as well as accompanying documentation.
pub struct Generator {
    pub(crate) templates: Tera,
    pub(crate) output_dir: PathBuf,
    pub(crate) modules: Vec<Module>,
}

impl Generator {
    /// Create a new generator pointing at the template directory and the
    /// desired output directory.
    pub fn new<P: AsRef<Path>>(templates_dir: P, output_dir: P) -> Result<Self> {
        let templates_path = templates_dir.as_ref().join("**/*");
        let templates_glob = templates_path
            .to_str()
            .context("Failed to convert templates path to string")?;

        let mut templates =
            Tera::new(templates_glob).context("Failed to initialize Tera template engine")?;
        templates.autoescape_on(vec![]);

        Ok(Self {
            templates,
            output_dir: output_dir.as_ref().to_path_buf(),
            modules: Vec::new(),
        })
    }

    /// Provide all modules for cross-references (e.g. validations)
    pub fn set_modules(&mut self, modules: Vec<Module>) {
        self.modules = modules;
    }

    /// Generate code for all nodes contained in the provided [`Module`].
    pub fn generate(&self, module: &Module) -> Result<()> {
        for node in &module.nodes {
            self.generate_node(module, node)?;
            self.generate_documentation(module, node)?;
        }

        // Additional battery templates
        self.generate_batteries(module)?;

        // Run post-processing tasks
        self.run_post_processing()
    }

    fn generate_node(&self, module: &Module, node: &Node) -> Result<()> {
        let ctx = GeneratorContext { generator: self, module, node };
        match node.node_type {
            NodeType::UseCase => UsecaseGenerator.generate(ctx),
            NodeType::Adapter => AdapterGenerator.generate(ctx),
            NodeType::Port => PortGenerator.generate(ctx),
            NodeType::Entity => EntityGenerator.generate(ctx),
            NodeType::Component => ComponentGenerator.generate(ctx),
            NodeType::Hook => HookGenerator.generate(ctx),
            NodeType::Schema => SchemaGenerator.generate(ctx),
            NodeType::Form => FormGenerator.generate(ctx),
            NodeType::Validation => ValidationGenerator.generate(ctx),
            NodeType::Upload => UploadGenerator.generate(ctx),
            NodeType::Iot => Ok(()),
            NodeType::Policy | NodeType::Resource => Ok(()),
        }
    }


    fn generate_batteries(&self, module: &Module) -> Result<()> {
        let ctx = BatteriesContext {
            module,
            module_name: &module.name,
        };
        let context =
            TeraContext::from_serialize(&ctx).context("Failed to serialize batteries context")?;

        if module.nodes.iter().any(|n| n.id == "authService") {
            let handler_content = self
                .templates
                .render("batteries/auth/backend/handlers/auth.rs.tera", &context)
                .context("Failed to render auth handler template")?;
            let handler_path = self.output_dir.join("backend/handlers").join("auth.rs");
            self.write_file(&handler_path, &handler_content)?;

            let route_content = self
                .templates
                .render("batteries/auth/backend/routes/auth.rs.tera", &context)
                .context("Failed to render auth routes template")?;
            let route_path = self.output_dir.join("backend/routes").join("auth.rs");
            self.write_file(&route_path, &route_content)?;

            let hook_content = self
                .templates
                .render("batteries/auth/frontend/hooks/useLogin.ts.tera", &context)
                .context("Failed to render useLogin hook template")?;
            let hook_path = self
                .output_dir
                .join("frontend/src/hooks")
                .join("useLogin.ts");
            self.write_file(&hook_path, &hook_content)?;

            let component_content = self
                .templates
                .render(
                    "batteries/auth/frontend/components/LoginForm.tsx.tera",
                    &context,
                )
                .context("Failed to render LoginForm component template")?;
            let component_path = self
                .output_dir
                .join("frontend/src/components")
                .join("LoginForm.tsx");
            self.write_file(&component_path, &component_content)?;
        }

        Ok(())
    }

    fn generate_documentation(&self, module: &Module, node: &Node) -> Result<()> {
        let ctx = DocumentationContext { module, node };
        let context = TeraContext::from_serialize(&ctx)
            .context("Failed to serialize documentation context")?;

        let doc_content = self
            .templates
            .render("docs/node.tera", &context)
            .context("Failed to render documentation template")?;

        let dir = match node.node_type {
            NodeType::Entity => "docs/db",
            NodeType::UseCase | NodeType::Upload => "docs/api",
            _ => "docs/modules",
        };

        let file_name = if matches!(node.node_type, NodeType::Entity) {
            format!("{}_entity.md", node.id)
        } else {
            format!("{}.md", node.id)
        };

        let doc_path = self.output_dir.join(dir).join(file_name);
        self.write_file(&doc_path, &doc_content)
    }

    pub(crate) fn write_file<P: AsRef<Path>>(&self, path: P, content: &str) -> Result<()> {
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
        use crate::{format_frontend, format_rust, CargoFmt, Prettier};
        use std::process::Command;

        // Attempt to run typeshare if available
        let types_output_dir = self.output_dir.join("frontend/src/types");
        let typeshare_status = Command::new("typeshare")
            .arg("--lang=typescript")
            .arg("--output-folder")
            .arg(&types_output_dir)
            .arg(self.output_dir.join("shared-models"))
            .status();
        if typeshare_status
            .as_ref()
            .map(|s| !s.success())
            .unwrap_or(true)
        {
            println!("⚠️  typeshare not available or failed, skipping TypeScript generation");
        }

        // Format generated sources using external tools when available
        format_rust(&CargoFmt, &self.output_dir);
        format_frontend(&Prettier, &self.output_dir.join("frontend"));

        Ok(())
    }
}

// Helper function to capitalize first letter of a string
pub(crate) fn capitalize(s: &str) -> String {
    let mut chars = s.chars();
    match chars.next() {
        None => String::new(),
        Some(first) => first.to_uppercase().collect::<String>() + chars.as_str(),
    }
}

pub(crate) fn snake_case(s: &str) -> String {
    let mut out = String::new();
    for (i, c) in s.chars().enumerate() {
        if c.is_uppercase() {
            if i != 0 {
                out.push('_');
            }
            for low in c.to_lowercase() {
                out.push(low);
            }
        } else {
            out.push(c);
        }
    }
    out
}

pub(crate) fn parse_validation_rule(rule: &str) -> ParsedRule {
    if let Some(pat) = rule.strip_prefix("regex ") {
        let pat = pat.trim().trim_start_matches('/').trim_end_matches('/');
        return ParsedRule {
            kind: "Regex".into(),
            pattern: Some(pat.to_string()),
            min: None,
            max: None,
        };
    }
    if let Some(range) = rule.strip_prefix("range ") {
        if let Some((min, max)) = range.split_once("..") {
            if let (Ok(min), Ok(max)) = (min.parse::<i32>(), max.parse::<i32>()) {
                return ParsedRule {
                    kind: "Range".into(),
                    pattern: None,
                    min: Some(min),
                    max: Some(max),
                };
            }
        }
    }
    ParsedRule {
        kind: "Custom".into(),
        pattern: None,
        min: None,
        max: None,
    }
}

#[cfg(test)]
mod tests {
    use super::{capitalize, parse_validation_rule, snake_case};

    #[test]
    fn test_capitalize() {
        assert_eq!(capitalize("hello"), "Hello");
        assert_eq!(capitalize(""), "");
    }

    #[test]
    fn test_snake_case() {
        assert_eq!(snake_case("HelloWorld"), "hello_world");
        assert_eq!(snake_case("test"), "test");
    }

    #[test]
    fn test_parse_validation_rule() {
        let r = parse_validation_rule("regex /@/");
        assert_eq!(r.kind, "Regex");
        assert_eq!(r.pattern.unwrap(), "@");
    }
}
