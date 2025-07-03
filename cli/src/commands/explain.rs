use anyhow::Result;
use std::path::PathBuf;

pub fn explain(file: PathBuf) -> Result<()> {
    let mut dsl = ferrum_compiler::parse_dsl_yaml(&file)?;
    let plugins = super::load_plugins()?;
    plugins.extend_dsl_all(&mut dsl)?;

    println!("Features:\n-----------");
    for f in &dsl.app.features {
        println!("- {}", f);
    }
    println!("\nResources:\n-----------");
    for r in &dsl.resources {
        println!("- {} ({})", r.name, r.resource_type);
    }
    println!("\nJobs:\n-----");
    for j in &dsl.jobs {
        println!("- {} -> {}", j.name, j.handler);
    }
    println!("\nRoutes:\n-------");
    for r in &dsl.routes {
        println!("- {} {}", r.name, r.path);
    }
    Ok(())
}

