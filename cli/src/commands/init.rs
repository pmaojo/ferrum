use anyhow::Result;
use std::path::{Path, PathBuf};

pub fn init(
    name: String,
    mut with_graph: bool,
    mut with_ai: bool,
    mut with_db: bool,
    mut with_auth: bool,
    mut with_jobs: bool,
    mut with_uploads: bool,
    mut frontend: super::Frontend,
    mut nostarter: bool,
    mut api_only: bool,
    interactive: bool,
) -> Result<()> {
    use std::fs::{self, OpenOptions};
    use std::io::Write;

    println!("🏗️  Initializing new Ferrum project: {}", name);
    println!("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━");

    if interactive {
        use dialoguer::Confirm;
        with_graph = Confirm::new()
            .with_prompt("Include graph database support?")
            .default(with_graph)
            .interact()?;
        with_ai = Confirm::new()
            .with_prompt("Include AI/LLM integration?")
            .default(with_ai)
            .interact()?;
        with_db = Confirm::new()
            .with_prompt("Include Diesel ORM setup?")
            .default(with_db)
            .interact()?;
        with_auth = Confirm::new()
            .with_prompt("Include authentication templates?")
            .default(with_auth)
            .interact()?;
        with_jobs = Confirm::new()
            .with_prompt("Include background job templates?")
            .default(with_jobs)
            .interact()?;
        with_uploads = Confirm::new()
            .with_prompt("Include file upload templates?")
            .default(with_uploads)
            .interact()?;
        use dialoguer::{Select};
        frontend = match Select::new()
            .with_prompt("Frontend framework")
            .default(match frontend {
                super::Frontend::React => 0,
                super::Frontend::LeptosCsr => 1,
                super::Frontend::LeptosSsr => 2,
            })
            .items(&["React", "Leptos CSR", "Leptos SSR"])
            .interact()?
        {
            1 => super::Frontend::LeptosCsr,
            2 => super::Frontend::LeptosSsr,
            _ => super::Frontend::React,
        };
        nostarter = Confirm::new()
            .with_prompt("Skip starter templates?")
            .default(nostarter)
            .interact()?;
        api_only = Confirm::new()
            .with_prompt("Backend only project (no frontend)?")
            .default(api_only)
            .interact()?;
        println!();
    }

    // Create project directory
    let project_dir = PathBuf::from(&name);
    fs::create_dir_all(&project_dir)?;

    // Create directory structure
    let mut dirs = vec![
        "backend/src",
        "shared-models",
        "templates/backend",
        "templates/shared-models",
        "gen",
        "data/postgres",
    ];
    if !api_only {
        match frontend {
            super::Frontend::React => {
                dirs.push("frontend/src");
                dirs.push("templates/frontend");
            }
            super::Frontend::LeptosCsr | super::Frontend::LeptosSsr => {
                dirs.push("frontend_leptos/src");
                dirs.push("frontend_leptos/src/pages");
                dirs.push("templates/frontend_leptos");
            }
        }
    }

    for dir in dirs.iter() {
        fs::create_dir_all(project_dir.join(dir))?;
        println!("📁 Created directory: {}/{}", name, dir);
    }

    // Basic backend skeleton
    fs::write(
        project_dir.join("backend/src/main.rs"),
        r#"use axum::{routing::get, Router};
use std::net::SocketAddr;

#[tokio::main]
async fn main() {
    let app = Router::new().route("/", get(|| async { "Hello Ferrum" }));

    let addr = SocketAddr::from(([0, 0, 0, 0], 3000));
    println!("🚀 backend running on {}", addr);
    axum::Server::bind(&addr)
        .serve(app.into_make_service())
        .await
        .unwrap();
}
"#,
    )?;
    fs::write(
        project_dir.join("backend/Cargo.toml"),
        r#"[package]
name = "backend"
version = "0.1.0"
edition = "2021"

[dependencies]
axum = "0.7"
tokio = { version = "1", features = ["full"] }
serde = { version = "1", features = ["derive"] }
embedded-hal = { version = "1", optional = true }
rppal = { version = "0.18", optional = true }
rumqttc = { version = "0.22", optional = true }
ethercat-rs = { version = "0.2", package = "ethercat_rs", optional = true }

[features]
default = []
hal = ["embedded-hal"]
rppal = ["rppal"]
mqtt = ["rumqttc"]
ethercat = ["ethercat-rs"]
"#,
    )?;

    if matches!(frontend, super::Frontend::LeptosCsr | super::Frontend::LeptosSsr) {
        fs::write(
            project_dir.join("Cargo.toml"),
            "[workspace]\nmembers = [\"backend\", \"frontend_leptos\"]\n",
        )?;
    }

    if !api_only && !nostarter {
        match frontend {
            super::Frontend::React => write_react_starter(&project_dir)?,
            super::Frontend::LeptosCsr | super::Frontend::LeptosSsr => {
                copy_leptos_starter(&project_dir, frontend)?
            }
        }
    }

    // Create additional directories based on flags
    if with_graph {
        fs::create_dir_all(project_dir.join("data/neo4j"))?;
        println!("📁 Created directory: {}/data/neo4j", name);
    }

    if with_ai {
        fs::create_dir_all(project_dir.join("data/ollama"))?;
        println!("📁 Created directory: {}/data/ollama", name);
    }

    if with_db {
        fs::create_dir_all(project_dir.join("backend/migrations"))?;
        fs::create_dir_all(project_dir.join("templates/backend/db/migrations"))?;
        println!("📁 Created directory: {}/backend/migrations", name);

        // Copy Diesel templates into project templates directory
        fs::write(
            project_dir.join("templates/backend/db/schema.rs.tera"),
            include_str!("../../../templates/backend/db/schema.rs.tera"),
        )?;
        fs::write(
            project_dir.join("templates/backend/db/models.rs.tera"),
            include_str!("../../../templates/backend/db/models.rs.tera"),
        )?;
        fs::write(
            project_dir.join("templates/backend/db/mod.rs.tera"),
            include_str!("../../../templates/backend/db/mod.rs.tera"),
        )?;

        // Copy optional seed data
        fs::create_dir_all(project_dir.join("templates/backend/db/seeds"))?;
        fs::write(
            project_dir.join("templates/backend/db/seeds/usuarios.sql"),
            include_str!("../../../templates/backend/db/seeds/usuarios.sql"),
        )?;

        fs::create_dir_all(project_dir.join("backend/seeds"))?;
        fs::write(
            project_dir.join("backend/seeds/usuarios.sql"),
            include_str!("../../../templates/backend/db/seeds/usuarios.sql"),
        )?;

        let mig_template_dir =
            project_dir.join("templates/backend/db/migrations/0001_create_usuarios");
        fs::create_dir_all(&mig_template_dir)?;
        fs::write(
            mig_template_dir.join("up.sql"),
            include_str!("../../../templates/backend/db/migrations/0001_create_usuarios/up.sql"),
        )?;
        fs::write(
            mig_template_dir.join("down.sql"),
            include_str!("../../../templates/backend/db/migrations/0001_create_usuarios/down.sql"),
        )?;

        let mig_dir = project_dir.join("backend/migrations/0001_create_usuarios");
        fs::create_dir_all(&mig_dir)?;
        fs::write(
            mig_dir.join("up.sql"),
            include_str!("../../../templates/backend/db/migrations/0001_create_usuarios/up.sql"),
        )?;
        fs::write(
            mig_dir.join("down.sql"),
            include_str!("../../../templates/backend/db/migrations/0001_create_usuarios/down.sql"),
        )?;

        // Create .env with database URL
        fs::write(
            project_dir.join(".env"),
            "DATABASE_URL=postgres://usuario:clave@localhost/ferrum_dev\n",
        )?;

        // Create diesel.toml for CLI configuration
        fs::write(
            project_dir.join("diesel.toml"),
            "[print_schema]\nfile = \"src/schema.rs\"\n",
        )?;

        // Create basic Makefile with DB init commands
        fs::write(
            project_dir.join("Makefile"),
            "db-init:\n\tdiesel setup\n\tdiesel migration generate create_usuarios\n",
        )?;

        println!("📄 Added Diesel templates and .env file");
    }

    if with_auth {
        fs::create_dir_all(project_dir.join("templates/batteries/auth"))?;
        fs::write(
            project_dir.join("templates/batteries/auth/login_handler.rs.tera"),
            include_str!("../../../templates/batteries/auth/login_handler.rs.tera"),
        )?;
        println!("📄 Added authentication templates");
    }

    if with_jobs {
        fs::create_dir_all(project_dir.join("templates/batteries/jobs"))?;
        fs::write(
            project_dir.join("templates/batteries/jobs/example_job.rs.tera"),
            include_str!("../../../templates/batteries/jobs/example_job.rs.tera"),
        )?;
        println!("📄 Added job templates");
    }

    if with_uploads {
        fs::create_dir_all(project_dir.join("templates/batteries/uploads"))?;
        fs::write(
            project_dir.join("templates/batteries/uploads/backend/handlers/upload.rs.tera"),
            include_str!("../../../templates/batteries/uploads/backend/handlers/upload.rs.tera"),
        )?;
        fs::write(
            project_dir.join("templates/batteries/uploads/backend/routes/uploads.rs.tera"),
            include_str!("../../../templates/batteries/uploads/backend/routes/uploads.rs.tera"),
        )?;
        fs::write(
            project_dir
                .join("templates/batteries/uploads/frontend/components/FileDropzone.tsx.tera"),
            include_str!(
                "../../../templates/batteries/uploads/frontend/components/FileDropzone.tsx.tera"
            ),
        )?;
        fs::write(
            project_dir.join("templates/batteries/uploads/frontend/hooks/useUploadFile.ts.tera"),
            include_str!("../../../templates/batteries/uploads/frontend/hooks/useUploadFile.ts.tera"),
        )?;
        println!("📄 Added upload templates");
    }

    // Create docker-compose.yml
    let mut docker_compose = fs::File::create(project_dir.join("docker-compose.yml"))?;
    let mut docker_compose_content = include_str!("../../../templates/docker-compose.yml").to_string();
    if api_only {
        let mut filtered = String::new();
        let mut skip = false;
        for line in docker_compose_content.lines() {
            if line.starts_with("  frontend:") {
                skip = true;
                continue;
            }
            if skip {
                if line.starts_with("  ") && !line.starts_with("    ") {
                    skip = false;
                } else {
                    continue;
                }
            }
            if !skip {
                filtered.push_str(line);
                filtered.push('\n');
            }
        }
        docker_compose_content = filtered;
    }
    if with_db {
        docker_compose_content.push_str("\n  diesel:\n    image: rust:latest\n    command: ['cargo', 'install', 'diesel_cli']\n");
    }
    docker_compose.write_all(docker_compose_content.as_bytes())?;
    println!("📄 Created docker-compose.yml");

    fs::write(
        project_dir.join("Dockerfile"),
        include_str!("../../../templates/Dockerfile"),
    )?;
    println!("📄 Created Dockerfile");

    fs::write(
        project_dir.join("compose.prod.yaml"),
        include_str!("../../../templates/compose.prod.yaml"),
    )?;
    println!("📄 Created compose.prod.yaml");

    if with_db {
        let dockerfile_path = project_dir.join("backend/Dockerfile");
        fs::create_dir_all(project_dir.join("backend"))?;
        fs::write(
            dockerfile_path,
            "FROM rust:latest\nRUN apt-get update && apt-get install -y libpq-dev \\n+    && cargo install diesel_cli --no-default-features --features postgres\nWORKDIR /app\n",
        )?;
        println!("📄 Created backend/Dockerfile with diesel_cli");
    }

    // Create example grafo.yaml
    let mut example_yaml = fs::File::create(project_dir.join("gen/example.yaml"))?;
    let example_yaml_content = include_str!("../../../gen/users.yaml");
    example_yaml.write_all(example_yaml_content.as_bytes())?;
    println!("📄 Created example grafo.yaml");

    if with_db {
        let cargo_toml_path = project_dir.join("backend/Cargo.toml");
        fs::create_dir_all(project_dir.join("backend"))?;
        let mut cargo_toml = OpenOptions::new()
            .create(true)
            .append(true)
            .open(&cargo_toml_path)?;
        writeln!(
            cargo_toml,
            "diesel = {{ version = \"2.1\", features = [\"postgres\", \"r2d2\"] }}"
        )?;
        writeln!(cargo_toml, "dotenvy = \"0.15\"")?;
        println!("📄 Updated backend/Cargo.toml with Diesel dependencies");
    }

    // Create README.md
    let mut readme = fs::File::create(project_dir.join("README.md"))?;
    let frontend_section = if api_only {
        String::new()
    } else {
        "- `frontend/`: React frontend with TypeScript\n".to_string()
    };
    let readme_content = format!(
        r#"# {}

An AI-first full-stack application scaffolded with Ferrum.

## Getting Started

```bash
# Start the development environment
ferrum dev

# With graph database
ferrum dev --with-graph

# With AI/LLM service
ferrum dev --with-ai
# With authentication templates
ferrum init myapp --with-auth

# With job templates
ferrum init myapp --with-jobs
```

## Database Setup

```bash
diesel setup       # create database
diesel migration run
```

Run optional seeds:

```bash
psql $DATABASE_URL -f backend/seeds/usuarios.sql
```

## Project Structure

- `backend/`: Rust backend using Axum
{frontend_section}- `shared-models/`: Shared models between backend and frontend
- `templates/`: Templates for code generation
- `gen/`: YAML architecture files
- `data/`: Persistent data for Docker services
"#,
        name,
        frontend_section = frontend_section
    );
    readme.write_all(readme_content.as_bytes())?;
    println!("📄 Created README.md");

    println!();
    println!("✅ Project initialized successfully!");
    let plugins = super::load_plugins()?;
    plugins.init_all()?;
    println!("📂 Project location: {}", project_dir.display());
    println!();
    println!("Next steps:");
    println!("  1. cd {}", name);
    println!("  2. ferrum compile gen/example.yaml");
    println!("  3. ferrum dev");

    Ok(())
}

fn write_react_starter(dir: &Path) -> Result<()> {
    use std::fs;
    fs::write(dir.join("frontend/package.json"), include_str!("../../../templates/frontend/package.json"))?;
    fs::write(dir.join("frontend/tsconfig.json"), include_str!("../../../templates/frontend/tsconfig.json"))?;
    fs::write(dir.join("frontend/vite.config.ts"), include_str!("../../../templates/frontend/vite.config.ts"))?;
    fs::write(dir.join("frontend/index.html"), include_str!("../../../templates/frontend/index.html"))?;
    fs::write(dir.join("frontend/src/index.css"), "")?;
    fs::write(dir.join("frontend/src/App.tsx"), "export default function App() {\n  return <h1>Ferrum app ready!</h1>;\n}\n")?;
    fs::write(dir.join("frontend/src/main.tsx"), include_str!("../../../templates/frontend/main.tsx"))?;
    Ok(())
}

fn copy_leptos_starter(dir: &Path, mode: super::Frontend) -> Result<()> {
    use std::fs;
    use walkdir::WalkDir;

    let subdir = match mode {
        super::Frontend::LeptosCsr => "csr",
        super::Frontend::LeptosSsr => "ssr",
        _ => unreachable!(),
    };

    let template_dir = PathBuf::from("templates/frontend_leptos").join(subdir);
    for entry in WalkDir::new(&template_dir) {
        let entry = entry?;
        if entry.file_type().is_file() {
            let rel = entry.path().strip_prefix(&template_dir)?;
            let dest = dir.join("frontend_leptos").join(rel);
            if dest.exists() {
                continue;
            }
            if let Some(parent) = dest.parent() {
                fs::create_dir_all(parent)?;
            }
            fs::copy(entry.path(), &dest)?;
        }
    }

    Ok(())
}

