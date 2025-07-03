use anyhow::Result;
use std::path::PathBuf;

pub fn generate_usecase(name: String, output: Option<PathBuf>) -> Result<()> {
    use std::fs;

    println!("📝 Generating usecase: {}", name);
    println!("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━");

    let module = name.to_lowercase();
    let yaml = format!(
        "module: {module}\nnodes:\n  - id: {id}\n    type: usecase\n    input:\n      - name: example\n        type: string\n",
        module = module,
        id = name
    );

    let default_path = format!("gen/{}_usecase.yaml", module);
    let output_path = output.unwrap_or_else(|| PathBuf::from(default_path));
    fs::create_dir_all(output_path.parent().unwrap())?;
    fs::write(&output_path, yaml)?;

    println!("✅ Usecase YAML generated at: {}", output_path.display());

    Ok(())
}

