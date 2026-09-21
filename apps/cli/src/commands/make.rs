use anyhow::{Context, Result};
use inflector::Inflector;
use std::collections::BTreeMap;
use std::fs;
use std::path::{Path, PathBuf};

use ferrum_shared_models::{DslJob, DslPolicy, DslResource, DslStandaloneEntity, FerrumDsl};

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

/// `ferrum make:entity NAME --field title:string --field body:text` — the
/// equivalent of `artisan make:model`/`rails generate model`: adds a
/// standalone entity to the DSL and generates its Rust model, TypeScript
/// schema, Diesel migration and Diesel ORM boilerplate immediately.
///
/// Unlike `make:resource`/`make:job`/`make:policy`, which call a per-item
/// generator function directly, entities are only rendered through the
/// Node-graph `Generator` (`generate_entity`), so this goes through the
/// same `project_to_modules` conversion `ferrum compile` uses and then
/// generates just the one resulting module instead of the whole project.
pub fn make_entity(
    name: String,
    fields: Vec<String>,
    derive_from: Option<String>,
    file: PathBuf,
    templates: Option<PathBuf>,
) -> Result<()> {
    let mut dsl = ferrum_compiler::parse_dsl_yaml(&file)?;
    if dsl.entities.iter().any(|e| e.name == name) {
        anyhow::bail!("an entity named '{name}' already exists in {}", file.display());
    }

    let mut field_map = BTreeMap::new();
    for f in &fields {
        let (fname, ftype) = f.split_once(':').with_context(|| {
            format!("field '{f}' must be in the form name:type, e.g. title:string")
        })?;
        field_map.insert(fname.to_string(), ftype.to_string());
    }

    dsl.entities.push(DslStandaloneEntity {
        name: name.clone(),
        derive_from,
        fields: field_map,
    });
    write_dsl_yaml(&file, &dsl)?;

    let modules = ferrum_compiler::project_to_modules(&mut dsl)?;
    let module = modules
        .into_iter()
        .find(|m| m.name == name)
        .context("internal error: entity module not found after DSL conversion")?;

    let templates_dir = templates.unwrap_or_else(|| PathBuf::from("templates"));
    let generator = ferrum_compiler::Generator::new(templates_dir, PathBuf::from("."))?;
    generator.generate(&module)?;

    let slug = name.to_lowercase();
    println!("✅ Added entity '{name}' to {}", file.display());
    println!("✅ Generated shared-models/{slug}.rs");
    println!("✅ Generated frontend/src/schemas/{slug}.ts");
    println!("✅ Generated backend/migrations/NNNN_create_{slug}/{{up,down}}.sql");
    println!("✅ Updated backend/src/db/{{models,schema}}.rs");
    Ok(())
}
