use anyhow::Result;
use std::path::PathBuf;

fn usecase_yaml(name: &str) -> String {
    let module = name.to_lowercase();
    format!(
        "app:\n  name: {module}\nmodules:\n  {module}:\n    usecases:\n      {id}:\n        input:\n          example: string\n        output: null\n        steps: []\n",
        module = module,
        id = name
    )
}

pub fn generate_usecase(name: String, output: Option<PathBuf>) -> Result<()> {
    use std::fs;

    println!("📝 Generating usecase: {}", name);
    println!("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━");

    // Emit the current DSL shape rather than the legacy `module`/`nodes`
    // shape. This makes the result immediately usable with `ferrum compile`.
    let module = name.to_lowercase();
    let yaml = usecase_yaml(&name);

    let default_path = format!("gen/{}_usecase.yaml", module);
    let output_path = output.unwrap_or_else(|| PathBuf::from(default_path));
    if let Some(parent) = output_path.parent().filter(|parent| !parent.as_os_str().is_empty()) {
        fs::create_dir_all(parent)?;
    }
    fs::write(&output_path, yaml)?;

    println!("✅ Usecase YAML generated at: {}", output_path.display());
    println!("   Next: ferrum compile {}", output_path.display());

    Ok(())
}

#[cfg(test)]
mod tests {
    use super::usecase_yaml;

    #[test]
    fn generated_usecase_uses_current_dsl_shape() {
        let yaml = usecase_yaml("CreateUser");
        assert!(yaml.contains("app:"));
        assert!(yaml.contains("modules:"));
        assert!(yaml.contains("CreateUser:"));
        assert!(yaml.contains("input:"));
        assert!(!yaml.contains("nodes:"));
    }
}

