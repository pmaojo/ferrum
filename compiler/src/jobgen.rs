use anyhow::Result;
use inflector::Inflector;
use std::fs;

use ferrum_shared_models::{DslJob, FerrumDsl};

use crate::{utils::handle_unauthorized_snippet, ProjectPaths};

pub fn generate_job(job: &DslJob, paths: &ProjectPaths) -> Result<()> {
    let func_name = job.name.to_snake_case();
    let backend_dir = paths.backend.join("jobs");
    fs::create_dir_all(&backend_dir)?;
    let policy_check = job
        .policy
        .as_ref()
        .map(|p| {
            format!(
                "    if !crate::policies::evaluate_policy(\"{p}\") {{\n        {}\n        return;\n    }}\n",
                handle_unauthorized_snippet(),
                p = p
            )
        })
        .unwrap_or_default();
    let content = format!(
        "// Scheduled: {}\n\npub async fn {}() {{\n{policy_check}    // ⛳️ AI_FILL[job_logic] --context=job:{orig}\n}}\n",
        job.schedule,
        func_name,
        policy_check = policy_check,
        orig = job.name,
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

#[cfg(test)]
mod tests {
    use super::*;
    use tempfile::tempdir;
    use std::fs;

    #[test]
    fn policy_check_uses_helper() {
        let dir = tempdir().unwrap();
        let paths = ProjectPaths::new(dir.path());
        let job = DslJob {
            name: "Cleanup".into(),
            schedule: "* * * * *".into(),
            handler: "./backend/jobs/cleanup.rs".into(),
            policy: Some("AdminOnly".into()),
        };
        generate_job(&job, &paths).unwrap();
        let content = fs::read_to_string(dir.path().join("backend/jobs/cleanup.rs")).unwrap();
        assert!(content.contains("handle_unauthorized()"));
    }
}
