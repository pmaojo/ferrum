use anyhow::{Context, Result};
use tera::Context as TeraContext;

use crate::generator::{parse_validation_rule, capitalize, snake_case, Generator};
use crate::template_context::*;
use ferrum_shared_models::{Module, Node};

/// Shared context passed to [`NodeGenerator::generate`].
pub struct GeneratorContext<'a> {
    pub generator: &'a Generator,
    pub module: &'a Module,
    pub node: &'a Node,
}

/// Trait implemented by all node generators.
pub trait NodeGenerator {
    fn generate(&self, ctx: GeneratorContext) -> Result<()>;
}

/// Generator for `UseCase` nodes.
pub struct UsecaseGenerator;
impl NodeGenerator for UsecaseGenerator {
    fn generate(&self, ctx: GeneratorContext) -> Result<()> {
        let gen = ctx.generator;
        let module = ctx.module;
        let node = ctx.node;
        let mut field_validations: Vec<FieldValidation> = Vec::new();
        if let Some(vmod) = gen.modules.iter().find(|m| m.name == "validations") {
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
        let ctx = UsecaseContext {
            module,
            node,
            module_name: &module.name,
            field_validations: if field_validations.is_empty() {
                None
            } else {
                Some(field_validations)
            },
        };
        let context = TeraContext::from_serialize(&ctx).context("Failed to serialize usecase context")?;
        let handler_content = gen.templates.render("backend/handler.tera", &context).context("Failed to render handler template")?;
        let handler_path = gen.output_dir.join("backend/handlers").join(format!("{}.rs", module.name));
        gen.write_file(&handler_path, &handler_content)?;
        let route_content = gen.templates.render("backend/route.tera", &context).context("Failed to render route template")?;
        let route_path = gen.output_dir.join("backend/routes").join(format!("{}.rs", module.name));
        gen.write_file(&route_path, &route_content)?;
        let hook_content = gen.templates.render("frontend/hook.tera", &context).context("Failed to render hook template")?;
        let hook_path = gen
            .output_dir
            .join("frontend/src/hooks")
            .join(format!("use{}.ts", capitalize(&node.id)));
        gen.write_file(&hook_path, &hook_content)?;
        let component_content = gen.templates.render("frontend/component.tera", &context).context("Failed to render component template")?;
        let component_path = gen
            .output_dir
            .join("frontend/src/components")
            .join(format!("{}.tsx", capitalize(&node.id)));
        gen.write_file(&component_path, &component_content)
    }
}

/// Generator for `Adapter` nodes.
pub struct AdapterGenerator;
impl NodeGenerator for AdapterGenerator {
    fn generate(&self, ctx: GeneratorContext) -> Result<()> {
        let gen = ctx.generator;
        let module = ctx.module;
        let node = ctx.node;
        let ctx = AdapterContext { module, node, module_name: &module.name };
        let context = TeraContext::from_serialize(&ctx).context("Failed to serialize adapter context")?;
        let adapter_content = gen.templates.render("backend/adapter.tera", &context).context("Failed to render adapter template")?;
        let adapter_path = gen.output_dir.join("backend/db").join(format!("{}.rs", module.name));
        gen.write_file(&adapter_path, &adapter_content)
    }
}

/// Generator for `Port` nodes.
pub struct PortGenerator;
impl NodeGenerator for PortGenerator {
    fn generate(&self, ctx: GeneratorContext) -> Result<()> {
        let gen = ctx.generator;
        let module = ctx.module;
        let node = ctx.node;
        let ctx = PortContext { module, node, module_name: &module.name };
        let context = TeraContext::from_serialize(&ctx).context("Failed to serialize port context")?;
        let port_content = gen.templates.render("backend/port.tera", &context).context("Failed to render port template")?;
        let port_path = gen.output_dir.join("backend/ports.rs");
        let existing_content = if port_path.exists() {
            std::fs::read_to_string(&port_path).unwrap_or_default()
        } else {
            String::new()
        };
        let updated_content = if existing_content.is_empty() {
            port_content
        } else {
            format!("{}{}", existing_content, port_content)
        };
        gen.write_file(&port_path, &updated_content)
    }
}

/// Generator for `Entity` nodes.
pub struct EntityGenerator;
impl NodeGenerator for EntityGenerator {
    fn generate(&self, ctx: GeneratorContext) -> Result<()> {
        let gen = ctx.generator;
        let module = ctx.module;
        let node = ctx.node;
        let ctx = EntityContext { module, node, module_name: &module.name };
        let context = TeraContext::from_serialize(&ctx).context("Failed to serialize entity context")?;
        let model_content = gen.templates.render("shared-models/model.tera", &context).context("Failed to render model template")?;
        let model_path = gen
            .output_dir
            .join("shared-models")
            .join(format!("{}.rs", node.id.to_lowercase()));
        gen.write_file(&model_path, &model_content)?;
        let schema_content = gen.templates.render("frontend/schema.tera", &context).context("Failed to render schema template")?;
        let schema_path = gen
            .output_dir
            .join("frontend/src/schemas")
            .join(format!("{}.ts", node.id.to_lowercase()));
        gen.write_file(&schema_path, &schema_content)?;
        let mig_root = gen.output_dir.join("backend/migrations");
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
            node.id.to_lowercase(),
            columns
        );
        std::fs::write(mig_dir.join("up.sql"), up_sql)?;
        let down_sql = format!("DROP TABLE {};", node.id.to_lowercase());
        std::fs::write(mig_dir.join("down.sql"), down_sql)?;
        use std::fs::OpenOptions;
        use std::io::Write;
        let db_dir = gen.output_dir.join("backend/src/db");
        std::fs::create_dir_all(&db_dir)?;
        let models_path = db_dir.join("models.rs");
        let schema_path = db_dir.join("schema.rs");
        let mod_path = db_dir.join("mod.rs");
        if !mod_path.exists() {
            gen.write_file(&mod_path, "pub mod models;\npub mod schema;\n")?;
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
        let diesel_ctx = DieselContext {
            table_name: node.id.to_lowercase(),
            struct_name: capitalize(&node.id),
            fields,
        };
        let diesel_ctx = TeraContext::from_serialize(&diesel_ctx).context("Failed to serialize Diesel context")?;
        let model_snippet = gen.templates.render("backend/db/models.rs.tera", &diesel_ctx).context("Failed to render Diesel model template")?;
        let schema_snippet = gen.templates.render("backend/db/schema.rs.tera", &diesel_ctx).context("Failed to render Diesel schema template")?;
        if !models_path.exists() {
            let mut f = OpenOptions::new().create(true).write(true).open(&models_path)?;
            writeln!(f, "use diesel::prelude::*;")?;
            writeln!(f, "use serde::{{Deserialize, Serialize}};")?;
            writeln!(f, "use uuid::Uuid;\n")?;
            f.write_all(model_snippet.as_bytes())?;
        } else {
            let mut f = OpenOptions::new().append(true).open(&models_path)?;
            writeln!(f)?;
            f.write_all(model_snippet.as_bytes())?;
        }
        let mut schema_file = OpenOptions::new().create(true).append(true).open(&schema_path)?;
        writeln!(schema_file, "{}", schema_snippet.trim_end())?;
        Ok(())
    }
}

/// Generator for `Component` nodes.
pub struct ComponentGenerator;
impl NodeGenerator for ComponentGenerator {
    fn generate(&self, ctx: GeneratorContext) -> Result<()> {
        let gen = ctx.generator;
        let module = ctx.module;
        let node = ctx.node;
        let ctx = ComponentContext { module, node, module_name: &module.name };
        let context = TeraContext::from_serialize(&ctx).context("Failed to serialize component context")?;
        let frontend_leptos = gen.output_dir.join("frontend_leptos").exists();
        if frontend_leptos {
            let content = gen.templates.render("frontend_leptos/component.rs.tera", &context).context("Failed to render component template")?;
            let path = gen
                .output_dir
                .join("frontend_leptos/src/components")
                .join(format!("{}.rs", capitalize(&node.id)));
            gen.write_file(&path, &content)
        } else {
            let component_content = gen.templates.render("frontend/component.tera", &context).context("Failed to render component template")?;
            let component_path = gen
                .output_dir
                .join("frontend/src/components")
                .join(format!("{}.tsx", capitalize(&node.id)));
            gen.write_file(&component_path, &component_content)
        }
    }
}

/// Generator for `Hook` nodes.
pub struct HookGenerator;
impl NodeGenerator for HookGenerator {
    fn generate(&self, ctx: GeneratorContext) -> Result<()> {
        let gen = ctx.generator;
        let module = ctx.module;
        let node = ctx.node;
        let ctx = HookContext { module, node, module_name: &module.name };
        let context = TeraContext::from_serialize(&ctx).context("Failed to serialize hook context")?;
        let hook_content = gen.templates.render("frontend/hook.tera", &context).context("Failed to render hook template")?;
        let hook_path = gen
            .output_dir
            .join("frontend/src/hooks")
            .join(format!("use{}.ts", capitalize(&node.id)));
        gen.write_file(&hook_path, &hook_content)
    }
}

/// Generator for `Schema` nodes.
pub struct SchemaGenerator;
impl NodeGenerator for SchemaGenerator {
    fn generate(&self, ctx: GeneratorContext) -> Result<()> {
        let gen = ctx.generator;
        let module = ctx.module;
        let node = ctx.node;
        let ctx = SchemaContext { module, node, module_name: &module.name };
        let context = TeraContext::from_serialize(&ctx).context("Failed to serialize schema context")?;
        let schema_content = gen.templates.render("frontend/schema.tera", &context).context("Failed to render schema template")?;
        let schema_path = gen
            .output_dir
            .join("frontend/src/schemas")
            .join(format!("{}.ts", node.id.to_lowercase()));
        gen.write_file(&schema_path, &schema_content)
    }
}

/// Generator for `Form` nodes.
pub struct FormGenerator;
impl NodeGenerator for FormGenerator {
    fn generate(&self, ctx: GeneratorContext) -> Result<()> {
        let gen = ctx.generator;
        let module = ctx.module;
        let node = ctx.node;
        let ctx = FormContext { module, node };
        let context = TeraContext::from_serialize(&ctx).context("Failed to serialize form context")?;
        let form_content = gen.templates.render("frontend/forms/form.tsx.tera", &context).context("Failed to render form template")?;
        let form_path = gen
            .output_dir
            .join("frontend/src/forms")
            .join(format!("{}.tsx", capitalize(&node.id)));
        gen.write_file(&form_path, &form_content)
    }
}

/// Generator for `Validation` nodes.
pub struct ValidationGenerator;
impl NodeGenerator for ValidationGenerator {
    fn generate(&self, ctx: GeneratorContext) -> Result<()> {
        let gen = ctx.generator;
        let module = ctx.module;
        let node = ctx.node;
        let rule = if let Some(rule) = &node.story {
            parse_validation_rule(rule)
        } else {
            ParsedRule { kind: "Custom".into(), pattern: None, min: None, max: None }
        };
        let fn_name = snake_case(&node.id);
        let ctx = ValidationContext { module, node, rule, fn_name: fn_name.clone() };
        let context = TeraContext::from_serialize(&ctx).context("Failed to serialize validation context")?;
        use std::fs::OpenOptions;
        let mod_path = gen.output_dir.join("backend/src/validations/mod.rs");
        if !mod_path.exists() {
            let mod_content = gen.templates.render("backend/validations/mod.rs.tera", &TeraContext::new()).context("Failed to render validations mod template")?;
            gen.write_file(&mod_path, &mod_content)?;
        }
        let mut mod_file = OpenOptions::new().append(true).open(&mod_path)?;
        use std::io::Write;
        writeln!(mod_file, "pub mod {};", fn_name)?;
        let custom_backend_path = gen.output_dir.join("backend/src/validations/custom.rs");
        if !custom_backend_path.exists() {
            let custom_content = gen.templates.render("backend/validations/custom.rs.tera", &TeraContext::new()).context("Failed to render custom validation template")?;
            gen.write_file(&custom_backend_path, &custom_content)?;
        }
        let custom_frontend_path = gen.output_dir.join("frontend/src/validations/custom.ts");
        if !custom_frontend_path.exists() {
            let custom_ts = gen.templates.render("frontend/validations/custom.ts.tera", &TeraContext::new()).context("Failed to render custom validation TS template")?;
            gen.write_file(&custom_frontend_path, &custom_ts)?;
        }
        let backend_content = gen.templates.render("backend/validations/validation.rs.tera", &context).context("Failed to render backend validation template")?;
        let backend_path = gen
            .output_dir
            .join("backend/src/validations")
            .join(format!("{}.rs", fn_name));
        gen.write_file(&backend_path, &backend_content)?;
        let frontend_content = gen.templates.render("frontend/validations/validation.ts.tera", &context).context("Failed to render frontend validation template")?;
        let frontend_path = gen
            .output_dir
            .join("frontend/src/validations")
            .join(format!("{}.ts", node.id));
        gen.write_file(&frontend_path, &frontend_content)
    }
}

/// Generator for `Upload` nodes.
pub struct UploadGenerator;
impl NodeGenerator for UploadGenerator {
    fn generate(&self, ctx: GeneratorContext) -> Result<()> {
        let gen = ctx.generator;
        let module = ctx.module;
        let node = ctx.node;
        let ctx = UploadContext { module, node };
        let context = TeraContext::from_serialize(&ctx).context("Failed to serialize upload context")?;
        let handler_content = gen
            .templates
            .render("batteries/uploads/backend/handlers/upload.rs.tera", &context)
            .context("Failed to render upload handler template")?;
        let handler_path = gen.output_dir.join("backend/handlers").join("upload.rs");
        gen.write_file(&handler_path, &handler_content)?;
        let route_content = gen
            .templates
            .render("batteries/uploads/backend/routes/uploads.rs.tera", &context)
            .context("Failed to render upload routes template")?;
        let route_path = gen.output_dir.join("backend/routes").join("uploads.rs");
        gen.write_file(&route_path, &route_content)?;
        let component_content = gen
            .templates
            .render("batteries/uploads/frontend/components/FileDropzone.tsx.tera", &context)
            .context("Failed to render FileDropzone template")?;
        let component_path = gen
            .output_dir
            .join("frontend/src/components")
            .join("FileDropzone.tsx");
        gen.write_file(&component_path, &component_content)?;
        let hook_content = gen
            .templates
            .render("batteries/uploads/frontend/hooks/useUploadFile.ts.tera", &context)
            .context("Failed to render useUploadFile template")?;
        let hook_path = gen
            .output_dir
            .join("frontend/src/hooks")
            .join("useUploadFile.ts");
        gen.write_file(&hook_path, &hook_content)
    }
}

