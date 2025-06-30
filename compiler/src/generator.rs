use anyhow::{Context, Result};
use std::fs;
use std::path::{Path, PathBuf};
use tera::{Context as TeraContext, Tera};

use ferrum_shared_models::{Module, Node, NodeType};

/// Code generator that materializes a graph of nodes into Rust and
/// TypeScript sources as well as accompanying documentation.
pub struct Generator {
    templates: Tera,
    output_dir: PathBuf,
    modules: Vec<Module>,
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
        match node.node_type {
            NodeType::UseCase => self.generate_usecase(module, node),
            NodeType::Adapter => self.generate_adapter(module, node),
            NodeType::Port => self.generate_port(module, node),
            NodeType::Entity => self.generate_entity(module, node),
            NodeType::Component => self.generate_component(module, node),
            NodeType::Hook => self.generate_hook(module, node),
            NodeType::Schema => self.generate_schema(module, node),
            NodeType::Form => self.generate_form(module, node),
            NodeType::Validation => self.generate_validation(module, node),
            NodeType::Upload => self.generate_upload(module, node),
            NodeType::Policy | NodeType::Resource => Ok(()),
        }
    }

    fn generate_usecase(&self, module: &Module, node: &Node) -> Result<()> {
        let mut context = TeraContext::new();
        context.insert("module", module);
        context.insert("node", node);
        // Add module name directly to context for templates
        context.insert("module_name", &module.name);

        // Collect validations for this usecase
        let mut field_validations: Vec<FieldValidation> = Vec::new();
        if let Some(vmod) = self.modules.iter().find(|m| m.name == "validations") {
            for val in &vmod.nodes {
                if let Some(applies) = &val.description {
                    for field in &node.input {
                        let expected = format!("{}.{}.{}", module.name, node.id, field.name);
                        if applies == &expected {
                            field_validations.push(FieldValidation {
                                field: field.name.clone(),
                                func: snake_case(&val.id),
                            });
                        }
                    }
                }
            }
        }
        if !field_validations.is_empty() {
            context.insert("field_validations", &field_validations);
        }

        // Generate handler
        let handler_content = self
            .templates
            .render("backend/handler.tera", &context)
            .context("Failed to render handler template")?;
        let handler_path = self
            .output_dir
            .join("backend/handlers")
            .join(format!("{}.rs", module.name));
        self.write_file(&handler_path, &handler_content)?;

        // Generate route
        let route_content = self
            .templates
            .render("backend/route.tera", &context)
            .context("Failed to render route template")?;
        let route_path = self
            .output_dir
            .join("backend/routes")
            .join(format!("{}.rs", module.name));
        self.write_file(&route_path, &route_content)?;

        // Generate frontend hook
        let hook_content = self
            .templates
            .render("frontend/hook.tera", &context)
            .context("Failed to render hook template")?;
        let hook_path = self
            .output_dir
            .join("frontend/src/hooks")
            .join(format!("use{}.ts", capitalize(&node.id)));
        self.write_file(&hook_path, &hook_content)?;

        // Generate frontend component
        let component_content = self
            .templates
            .render("frontend/component.tera", &context)
            .context("Failed to render component template")?;
        let component_path = self
            .output_dir
            .join("frontend/src/components")
            .join(format!("{}.tsx", capitalize(&node.id)));
        self.write_file(&component_path, &component_content)?;

        Ok(())
    }

    fn generate_adapter(&self, module: &Module, node: &Node) -> Result<()> {
        let mut context = TeraContext::new();
        context.insert("module", module);
        context.insert("node", node);
        context.insert("module_name", &module.name);

        let adapter_content = self
            .templates
            .render("backend/adapter.tera", &context)
            .context("Failed to render adapter template")?;
        let adapter_path = self
            .output_dir
            .join("backend/db")
            .join(format!("{}.rs", module.name));
        self.write_file(&adapter_path, &adapter_content)?;

        Ok(())
    }

    fn generate_port(&self, module: &Module, node: &Node) -> Result<()> {
        let mut context = TeraContext::new();
        context.insert("module", module);
        context.insert("node", node);
        context.insert("module_name", &module.name);

        let port_content = self
            .templates
            .render("backend/port.tera", &context)
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
        let model_content = self
            .templates
            .render("shared-models/model.tera", &context)
            .context("Failed to render model template")?;
        let model_path = self
            .output_dir
            .join("shared-models")
            .join(format!("{}.rs", node.id.to_lowercase()));
        self.write_file(&model_path, &model_content)?;

        // Generate TypeScript schema
        let schema_content = self
            .templates
            .render("frontend/schema.tera", &context)
            .context("Failed to render schema template")?;
        let schema_path = self
            .output_dir
            .join("frontend/src/schemas")
            .join(format!("{}.ts", node.id.to_lowercase()));
        self.write_file(&schema_path, &schema_content)?;

        // Generate Diesel migration based on entity fields
        let mig_root = self.output_dir.join("backend/migrations");
        std::fs::create_dir_all(&mig_root)?;
        let mig_idx = std::fs::read_dir(&mig_root)?.count() + 1;
        let mig_dir = mig_root.join(format!("{:04}_create_{}", mig_idx, node.id.to_lowercase()));
        std::fs::create_dir_all(&mig_dir)?;

        let mut columns = String::new();
        for field in &node.input {
            let sql_type = match field.field_type.as_str() {
                "uuid" => "UUID",
                "int" | "integer" => "INTEGER",
                "bool" => "BOOLEAN",
                "timestamp" => "TIMESTAMP",
                _ => "TEXT",
            };
            columns.push_str(&format!("    {} {} NOT NULL,\n", field.name, sql_type));
        }
        let up_sql = format!(
            "CREATE TABLE {} (\n    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),\n{}    created_at TIMESTAMP DEFAULT now()\n);\n",
            node.id.to_lowercase(), columns
        );
        std::fs::write(mig_dir.join("up.sql"), up_sql)?;
        let down_sql = format!("DROP TABLE {};", node.id.to_lowercase());
        std::fs::write(mig_dir.join("down.sql"), down_sql)?;

        // ---------------- Diesel ORM generation ----------------
        use std::fs::OpenOptions;
        use std::io::Write;

        let db_dir = self.output_dir.join("backend/src/db");
        std::fs::create_dir_all(&db_dir)?;
        let models_path = db_dir.join("models.rs");
        let schema_path = db_dir.join("schema.rs");
        let mod_path = db_dir.join("mod.rs");

        if !mod_path.exists() {
            self.write_file(&mod_path, "pub mod models;\npub mod schema;\n")?;
        }

        // Prepare field metadata for templates
        #[derive(serde::Serialize)]
        struct DieselField {
            name: String,
            rust_type: String,
            sql_type: String,
        }
        let fields: Vec<DieselField> = node
            .input
            .iter()
            .map(|f| DieselField {
                name: f.name.clone(),
                rust_type: match f.field_type.as_str() {
                    "uuid" => "Uuid".into(),
                    "int" | "integer" => "i32".into(),
                    "bool" => "bool".into(),
                    "timestamp" => "chrono::NaiveDateTime".into(),
                    _ => "String".into(),
                },
                sql_type: match f.field_type.as_str() {
                    "uuid" => "Uuid".into(),
                    "int" | "integer" => "Integer".into(),
                    "bool" => "Bool".into(),
                    "timestamp" => "Timestamp".into(),
                    _ => "Text".into(),
                },
            })
            .collect();

        let mut diesel_ctx = TeraContext::new();
        diesel_ctx.insert("table_name", &node.id.to_lowercase());
        diesel_ctx.insert("struct_name", &capitalize(&node.id));
        diesel_ctx.insert("fields", &fields);

        let model_snippet = self
            .templates
            .render("backend/db/models.rs.tera", &diesel_ctx)
            .context("Failed to render Diesel model template")?;
        let schema_snippet = self
            .templates
            .render("backend/db/schema.rs.tera", &diesel_ctx)
            .context("Failed to render Diesel schema template")?;

        if !models_path.exists() {
            let mut f = OpenOptions::new()
                .create(true)
                .write(true)
                .open(&models_path)?;
            writeln!(f, "use diesel::prelude::*;")?;
            writeln!(f, "use serde::{{Deserialize, Serialize}};")?;
            writeln!(f, "use uuid::Uuid;\n")?;
            f.write_all(model_snippet.as_bytes())?;
        } else {
            let mut f = OpenOptions::new().append(true).open(&models_path)?;
            writeln!(f)?;
            f.write_all(model_snippet.as_bytes())?;
        }

        let mut schema_file = OpenOptions::new()
            .create(true)
            .append(true)
            .open(&schema_path)?;
        writeln!(schema_file, "{}", schema_snippet.trim_end())?;

        Ok(())
    }

    fn generate_component(&self, module: &Module, node: &Node) -> Result<()> {
        let mut context = TeraContext::new();
        context.insert("module", module);
        context.insert("node", node);
        context.insert("module_name", &module.name);

        let component_content = self
            .templates
            .render("frontend/component.tera", &context)
            .context("Failed to render component template")?;
        let component_path = self
            .output_dir
            .join("frontend/src/components")
            .join(format!("{}.tsx", capitalize(&node.id)));
        self.write_file(&component_path, &component_content)
    }

    fn generate_hook(&self, module: &Module, node: &Node) -> Result<()> {
        let mut context = TeraContext::new();
        context.insert("module", module);
        context.insert("node", node);
        context.insert("module_name", &module.name);

        let hook_content = self
            .templates
            .render("frontend/hook.tera", &context)
            .context("Failed to render hook template")?;
        let hook_path = self
            .output_dir
            .join("frontend/src/hooks")
            .join(format!("use{}.ts", capitalize(&node.id)));
        self.write_file(&hook_path, &hook_content)
    }

    fn generate_schema(&self, module: &Module, node: &Node) -> Result<()> {
        let mut context = TeraContext::new();
        context.insert("module", module);
        context.insert("node", node);
        context.insert("module_name", &module.name);

        let schema_content = self
            .templates
            .render("frontend/schema.tera", &context)
            .context("Failed to render schema template")?;
        let schema_path = self
            .output_dir
            .join("frontend/src/schemas")
            .join(format!("{}.ts", node.id.to_lowercase()));
        self.write_file(&schema_path, &schema_content)
    }

    fn generate_form(&self, module: &Module, node: &Node) -> Result<()> {
        let mut context = TeraContext::new();
        context.insert("module", module);
        context.insert("node", node);

        let form_content = self
            .templates
            .render("frontend/forms/form.tsx.tera", &context)
            .context("Failed to render form template")?;
        let form_path = self
            .output_dir
            .join("frontend/src/forms")
            .join(format!("{}.tsx", capitalize(&node.id)));
        self.write_file(&form_path, &form_content)
    }

    fn generate_validation(&self, module: &Module, node: &Node) -> Result<()> {
        let mut context = TeraContext::new();
        context.insert("module", module);
        context.insert("node", node);
        if let Some(rule) = &node.story {
            let parsed = parse_validation_rule(rule);
            context.insert("rule", &parsed);
        } else {
            context.insert(
                "rule",
                &ParsedRule {
                    kind: "Custom".into(),
                    pattern: None,
                    min: None,
                    max: None,
                },
            );
        }
        let fn_name = snake_case(&node.id);
        context.insert("fn_name", &fn_name);

        let backend_content = self
            .templates
            .render("backend/validations/validation.rs.tera", &context)
            .context("Failed to render backend validation template")?;
        let backend_path = self
            .output_dir
            .join("backend/src/validations")
            .join(format!("{}.rs", fn_name));
        self.write_file(&backend_path, &backend_content)?;

        let frontend_content = self
            .templates
            .render("frontend/validations/validation.ts.tera", &context)
            .context("Failed to render frontend validation template")?;
        let frontend_path = self
            .output_dir
            .join("frontend/src/validations")
            .join(format!("{}.ts", node.id));
        self.write_file(&frontend_path, &frontend_content)
    }

    fn generate_upload(&self, module: &Module, node: &Node) -> Result<()> {
        let mut context = TeraContext::new();
        context.insert("module", module);
        context.insert("node", node);

        let handler_content = self
            .templates
            .render(
                "batteries/uploads/backend/handlers/upload.rs.tera",
                &context,
            )
            .context("Failed to render upload handler template")?;
        let handler_path = self.output_dir.join("backend/handlers").join("upload.rs");
        self.write_file(&handler_path, &handler_content)?;

        let route_content = self
            .templates
            .render("batteries/uploads/backend/routes/uploads.rs.tera", &context)
            .context("Failed to render upload routes template")?;
        let route_path = self.output_dir.join("backend/routes").join("uploads.rs");
        self.write_file(&route_path, &route_content)?;

        let component_content = self
            .templates
            .render(
                "batteries/uploads/frontend/components/FileDropzone.tsx.tera",
                &context,
            )
            .context("Failed to render FileDropzone template")?;
        let component_path = self
            .output_dir
            .join("frontend/src/components")
            .join("FileDropzone.tsx");
        self.write_file(&component_path, &component_content)?;

        let hook_content = self
            .templates
            .render(
                "batteries/uploads/frontend/hooks/useUploadFile.ts.tera",
                &context,
            )
            .context("Failed to render useUploadFile template")?;
        let hook_path = self
            .output_dir
            .join("frontend/src/hooks")
            .join("useUploadFile.ts");
        self.write_file(&hook_path, &hook_content)
    }

    fn generate_batteries(&self, module: &Module) -> Result<()> {
        let mut context = TeraContext::new();
        context.insert("module", module);
        context.insert("module_name", &module.name);

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
        let mut context = TeraContext::new();
        context.insert("module", module);
        context.insert("node", node);

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
        use std::process::Command;

        // Attempt to run typeshare if available
        let types_output_dir = self.output_dir.join("frontend/src/types");
        let typeshare_status = Command::new("typeshare")
            .arg("--lang=typescript")
            .arg("--output-dir")
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

        // Format Rust code
        let fmt_status = Command::new("cargo")
            .arg("fmt")
            .arg("--all")
            .current_dir(&self.output_dir)
            .status();
        if fmt_status.as_ref().map(|s| !s.success()).unwrap_or(true) {
            println!("⚠️  cargo fmt failed or is unavailable");
        }

        // Format frontend files with prettier if installed
        let prettier_status = Command::new("prettier")
            .arg("--write")
            .arg(self.output_dir.join("frontend").to_str().unwrap())
            .status();
        if prettier_status
            .as_ref()
            .map(|s| !s.success())
            .unwrap_or(true)
        {
            println!("⚠️  prettier failed or is unavailable");
        }

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

#[derive(Debug, serde::Serialize)]
struct ParsedRule {
    kind: String,
    pattern: Option<String>,
    min: Option<i32>,
    max: Option<i32>,
}

#[derive(Debug, serde::Serialize)]
struct FieldValidation {
    field: String,
    func: String,
}

fn parse_validation_rule(rule: &str) -> ParsedRule {
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
