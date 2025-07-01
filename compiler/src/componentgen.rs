use anyhow::Result;
use std::fs;

use ferrum_shared_models::{FerrumDsl, SharedComponent};

use crate::querygen::ProjectPaths;

/// Map primitive field types from the DSL to TypeScript types.
fn ts_type(field: &str) -> &str {
    match field {
        "string" => "string",
        "number" | "float" | "int" | "uint" | "usize" | "u32" | "i32" => "number",
        "bool" | "boolean" => "boolean",
        _ => field,
    }
}

/// Generate a React component file for a [`SharedComponent`].
pub fn generate_component(comp: &SharedComponent, paths: &ProjectPaths) -> Result<()> {
    let dir = paths.frontend.join("components");
    fs::create_dir_all(&dir)?;
    let mut props_interface = String::new();
    props_interface.push_str(&format!("export interface {}Props {{\n", comp.name));
    for p in &comp.props {
        props_interface.push_str(&format!("    {}: {};\n", p.name, ts_type(&p.field_type)));
    }
    props_interface.push_str("}\n\n");

    let params = comp
        .props
        .iter()
        .map(|p| p.name.as_str())
        .collect::<Vec<_>>()
        .join(", ");

    let content = format!(
        "{props_interface}export function {name}({{{params}}}: {name}Props) {{\n    return (\n        <div className=\"p-4 border rounded-lg bg-white shadow-sm {name}\">\n            <h2 className=\"text-xl font-semibold mb-2\">{name}</h2>\n            <div className=\"space-y-2\">\n                {{/* Component content */}}\n            </div>\n        </div>\n    );\n}}\n",
        props_interface = props_interface,
        name = comp.name,
        params = params
    );
    fs::write(dir.join(format!("{}.tsx", comp.name)), content)?;
    Ok(())
}

/// Generate an index.ts file exporting all components.
pub fn generate_index(comps: &[SharedComponent], paths: &ProjectPaths) -> Result<()> {
    let dir = paths.frontend.join("components");
    fs::create_dir_all(&dir)?;
    let mut content = String::new();
    for c in comps {
        content.push_str(&format!("export * from './{}';\n", c.name));
    }
    fs::write(dir.join("index.ts"), content)?;
    Ok(())
}

/// Generate a simple markdown file documenting component props.
pub fn generate_docs(comp: &SharedComponent, paths: &ProjectPaths) -> Result<()> {
    let dir = paths.frontend.join("components/docs");
    fs::create_dir_all(&dir)?;
    let mut content = format!("# {}\n\n", comp.name);
    if !comp.props.is_empty() {
        content.push_str("## Props\n\n");
        for p in &comp.props {
            content.push_str(&format!("- `{}`: `{}`\n", p.name, p.field_type));
        }
    }
    fs::write(dir.join(format!("{}.md", comp.name)), content)?;
    Ok(())
}

/// Compile all shared components in the DSL.
pub fn compile_components(dsl: &FerrumDsl, paths: &ProjectPaths) -> Result<()> {
    for c in &dsl.components {
        generate_component(c, paths)?;
        generate_docs(c, paths)?;
    }
    if !dsl.components.is_empty() {
        generate_index(&dsl.components, paths)?;
    }
    Ok(())
}

#[cfg(test)]
mod tests {
    use super::*;
    use tempfile::tempdir;

    #[test]
    fn generate_component_creates_files() {
        let dir = tempdir().unwrap();
        let paths = ProjectPaths::new(dir.path());
        let comp = SharedComponent {
            name: "Card".into(),
            props: vec![
                ferrum_shared_models::Field {
                    name: "title".into(),
                    field_type: "string".into(),
                },
                ferrum_shared_models::Field {
                    name: "count".into(),
                    field_type: "number".into(),
                },
            ],
        };
        generate_component(&comp, &paths).unwrap();
        assert!(dir.path().join("frontend/components/Card.tsx").exists());
        generate_index(&[comp.clone()], &paths).unwrap();
        assert!(dir.path().join("frontend/components/index.ts").exists());
        generate_docs(&comp, &paths).unwrap();
        assert!(dir.path().join("frontend/components/docs/Card.md").exists());
    }
}
