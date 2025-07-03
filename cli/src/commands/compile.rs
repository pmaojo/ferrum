use anyhow::Result;
use std::path::PathBuf;

pub fn compile(
    files: Vec<String>,
    output: Option<PathBuf>,
    templates: Option<PathBuf>,
    module: Option<String>,
    graph: bool,
) -> Result<()> {
    use glob::glob;

    let output_dir = output.unwrap_or_else(|| PathBuf::from("."));
    let templates_dir = templates.unwrap_or_else(|| PathBuf::from("templates"));
    let plugins = super::load_plugins()?;

    let mut paths = Vec::new();
    for pattern in files {
        for entry in glob(&pattern)? {
            match entry {
                Ok(p) => paths.push(p),
                Err(e) => println!("⚠️ glob error: {}", e),
            }
        }
    }

    for file in &paths {
        if graph {
            let content = std::fs::read_to_string(file)?;
            let nodes: Vec<ferrum_shared_models::Node> = serde_yaml::from_str(&content)?;
            let module_name = module.clone().unwrap_or_else(|| "subgraph".to_string());
            let graph_module = ferrum_shared_models::Module {
                name: module_name,
                nodes,
            };
            ferrum_compiler::validate_module(&graph_module)?;
            let generator = ferrum_compiler::Generator::new(templates_dir.clone(), output_dir.clone())?;
            generator.generate(&graph_module)?;
            println!("✅ Successfully compiled {}", file.display());
            plugins.compile_all()?;
            continue;
        }

        // Try new DSL format first, fall back to legacy format
        if let Ok(mut project) = ferrum_compiler::parse_dsl_yaml(file) {
            plugins.extend_dsl_all(&mut project)?;
            let modules = ferrum_compiler::project_to_modules(&mut project);
            ferrum_compiler::validate_modules(&modules)?;
            ferrum_compiler::validate_features(&project, &modules)?;
            ferrum_compiler::validate_validations(&project, &modules)?;
            let mut generator = ferrum_compiler::Generator::new(templates_dir.clone(), output_dir.clone())?;
            generator.set_modules(modules.clone());
            let target_modules: Vec<_> = if let Some(ref name) = module {
                modules.into_iter().filter(|m| m.name == *name).collect()
            } else {
                modules
            };
            for m in &target_modules {
                ferrum_compiler::validate_module(m)?;
                generator.generate(m)?;
            }
            if module.is_none() {
                let paths = ferrum_compiler::ProjectPaths::new(&output_dir);
                ferrum_compiler::compile_dsl(&project, &paths)?;
            }
        } else {
            let module_struct = ferrum_compiler::parse_yaml(file)?;
            if module.as_deref().map(|n| n != module_struct.name).unwrap_or(false) {
                continue;
            }
            ferrum_compiler::validate_module(&module_struct)?;

            let generator = ferrum_compiler::Generator::new(templates_dir.clone(), output_dir.clone())?;
            generator.generate(&module_struct)?;
        }

        println!("✅ Successfully compiled {}", file.display());
        plugins.compile_all()?;
    }

    use std::process::Command;

    // Format Rust code with cargo fmt if available
    match Command::new("cargo")
        .arg("fmt")
        .current_dir(&output_dir)
        .status()
    {
        Ok(status) if status.success() => {},
        Ok(_) => println!("⚠️  'cargo fmt' failed to format generated code"),
        Err(_) => println!("⚠️  'cargo fmt' not found; skipping Rust formatting"),
    }

    // Format TypeScript/JS code with prettier if available
    match Command::new("prettier")
        .arg("--write")
        .arg(output_dir.join("frontend"))
        .status()
    {
        Ok(status) if status.success() => {},
        Ok(_) => println!("⚠️  'prettier' failed to format TypeScript files"),
        Err(_) => println!("⚠️  'prettier' not found; skipping TypeScript formatting"),
    }

    let index = output_dir.join("frontend/index.html");
    if index.exists() {
        let _ = webbrowser::open(index.to_str().unwrap_or(""));
    }

    Ok(())
}
