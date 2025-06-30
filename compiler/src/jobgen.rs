use anyhow::Result;
use inflector::Inflector;
use std::fs;

use ferrum_shared_models::{DslJob, FerrumDsl};

use crate::querygen::ProjectPaths;

pub fn generate_job(job: &DslJob, paths: &ProjectPaths) -> Result<()> {
    let func_name = job.name.to_snake_case();
    let backend_dir = paths.backend.join("jobs");
    fs::create_dir_all(&backend_dir)?;
    let policy_check = job
        .policy
        .as_ref()
        .map(|p| format!("    if !crate::policies::evaluate_policy(\"{p}\") {{\n        // TODO: unauthorized handling\n        return;\n    }}\n", p = p))
        .unwrap_or_default();
    let content = format!(
        "// Scheduled: {}\n\npub async fn {}() {{\n{policy_check}    // TODO implement\n}}\n",
        job.schedule,
        func_name,
        policy_check = policy_check
    );
    fs::write(backend_dir.join(format!("{}.rs", func_name)), content)?;
    Ok(())
}

pub fn compile_jobs(dsl: &FerrumDsl, paths: &ProjectPaths) -> Result<()> {
    for job in &dsl.jobs {
        generate_job(job, paths)?;
    }
    Ok(())
}
