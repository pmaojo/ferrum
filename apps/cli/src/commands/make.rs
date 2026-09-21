use anyhow::{Context, Result};
use inflector::Inflector;
use std::fs;
use std::path::Path;

use ferrum_shared_models::{DslJob, DslPolicy, DslResource, FerrumDsl};

/// Write `dsl` back to `path` as YAML, overwriting the file in place.
///
/// This is the DSL-level equivalent of a Rails/Artisan generator editing
/// `db/schema.rb` or `routes.php`: the YAML file stays the single source of
/// truth, and `ferrum compile` on it later reproduces exactly what the
/// generator just wrote directly to `backend/`.
fn write_dsl_yaml(path: &Path, dsl: &FerrumDsl) -> Result<()> {
    let content = serde_yaml::to_string(dsl)
        .with_context(|| format!("Failed to serialize DSL back to {}", path.display()))?;
    fs::write(path, content)
        .with_context(|| format!("Failed to write DSL file: {}", path.display()))
}

/// `ferrum make:resource NAME --resource-type TYPE` — the equivalent of
/// `artisan make:model`/`rails generate model` for a backend resource
/// client (redis, s3, ...): adds it to the DSL and generates the file
/// immediately, instead of requiring a separate `ferrum compile` step.
pub fn make_resource(name: String, resource_type: String, file: std::path::PathBuf) -> Result<()> {
    let mut dsl = ferrum_compiler::parse_dsl_yaml(&file)?;
    if dsl.resources.iter().any(|r| r.name == name) {
        anyhow::bail!("a resource named '{name}' already exists in {}", file.display());
    }

    let resource = DslResource {
        name: name.clone(),
        resource_type,
        config: Default::default(),
    };
    dsl.resources.push(resource.clone());
    write_dsl_yaml(&file, &dsl)?;

    let paths = ferrum_compiler::ProjectPaths::new(".");
    ferrum_compiler::generate_resource(&resource, &paths)?;

    println!("✅ Added resource '{name}' to {}", file.display());
    println!(
        "✅ Generated backend/resources/{}.rs",
        name.to_lowercase()
    );
    Ok(())
}

/// `ferrum make:job NAME --schedule "0 0 * * *"` — a scheduled job, the
/// equivalent of `artisan make:command` wired into the scheduler or
/// `rails generate job`.
pub fn make_job(
    name: String,
    schedule: String,
    handler: Option<String>,
    file: std::path::PathBuf,
) -> Result<()> {
    let mut dsl = ferrum_compiler::parse_dsl_yaml(&file)?;
    if dsl.jobs.iter().any(|j| j.name == name) {
        anyhow::bail!("a job named '{name}' already exists in {}", file.display());
    }

    let job = DslJob {
        name: name.clone(),
        schedule,
        handler: handler.unwrap_or_else(|| name.clone()),
        policy: None,
    };
    dsl.jobs.push(job.clone());
    write_dsl_yaml(&file, &dsl)?;

    let paths = ferrum_compiler::ProjectPaths::new(".");
    ferrum_compiler::generate_job(&job, &paths)?;

    println!("✅ Added job '{name}' to {}", file.display());
    println!("✅ Generated backend/jobs/{}.rs", name.to_snake_case());
    Ok(())
}

/// `ferrum make:policy NAME --guard "role:admin"` — an authorization guard,
/// the equivalent of `artisan make:policy`.
pub fn make_policy(name: String, guard: String, file: std::path::PathBuf) -> Result<()> {
    let mut dsl = ferrum_compiler::parse_dsl_yaml(&file)?;
    if dsl.policies.iter().any(|p| p.name == name) {
        anyhow::bail!("a policy named '{name}' already exists in {}", file.display());
    }

    let policy = DslPolicy {
        name: name.clone(),
        guard,
    };
    dsl.policies.push(policy.clone());
    write_dsl_yaml(&file, &dsl)?;

    let paths = ferrum_compiler::ProjectPaths::new(".");
    ferrum_compiler::generate_policy(&policy, &paths)?;

    println!("✅ Added policy '{name}' to {}", file.display());
    println!("✅ Generated backend/policies/{}.rs", name.to_lowercase());
    Ok(())
}
