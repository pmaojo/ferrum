use anyhow::Result;
use std::path::{Path, PathBuf};

pub fn init(
    name: String,
    mut with_graph: bool,
    mut with_ai: bool,
    mut with_db: bool,
    mut db_type: super::DbType,
    mut with_auth: bool,
    mut with_jobs: bool,
    mut with_uploads: bool,
    mut frontend: super::Frontend,
    mut nostarter: bool,
    mut api_only: bool,
    interactive: bool,
) -> Result<()> {
    use std::fs::{self};
    use std::io::Write;

    println!("🏗️  Initializing new Ferrum project: {}", name);
    println!("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━");

    if interactive {
        use dialoguer::{Confirm, Select};
        with_graph = Confirm::new()
            .with_prompt("Include graph database support?")
            .default(with_graph)
            .interact()?;
        with_ai = Confirm::new()
            .with_prompt("Include AI/LLM integration?")
            .default(with_ai)
            .interact()?;

        // AI implies DB
        if with_ai && !with_db {
             println!("ℹ️  AI integration requires database support. Enabling Diesel ORM.");
             with_db = true;
        }

        with_db = Confirm::new()
            .with_prompt("Include Diesel ORM setup?")
            .default(with_db)
            .interact()?;
        if with_db {
            db_type = match Select::new()
                .with_prompt("Database type")
                .default(0)
                .items(&["PostgreSQL", "SQLite"])
                .interact()?
            {
                1 => super::DbType::Sqlite,
                _ => super::DbType::Postgres,
            };
        }
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
        frontend = match Select::new()
            .with_prompt("Frontend framework")
            .default(match frontend {
                super::Frontend::React => 0,
                super::Frontend::Egui => 1,
                super::Frontend::LeptosCsr => 2,
                super::Frontend::LeptosSsr => 3,
            })
            .items(&["React (web)", "EGUI (native desktop)", "Leptos CSR", "Leptos SSR"])
            .interact()?
        {
            1 => super::Frontend::Egui,
            2 => super::Frontend::LeptosCsr,
            3 => super::Frontend::LeptosSsr,
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

    // Create workspace Cargo.toml for EGUI projects
    if !api_only && matches!(frontend, super::Frontend::Egui) {
        fs::write(
            project_dir.join("Cargo.toml"),
            r#"[workspace]
members = [
    "backend",
    "frontend_egui",
    "shared-models",
]

[workspace.package]
version = "0.1.0"
edition = "2021"
"#,
        )?;
        println!("📄 Created workspace Cargo.toml");
    }

    // Create directory structure
    let mut dirs = vec![
        "backend/src",
        "backend/tests",
        "shared-models/src",
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
            super::Frontend::Egui => {
                dirs.push("frontend_egui/src");
                dirs.push("frontend_egui/src/views");
                dirs.push("frontend_egui/src/forms");
                dirs.push("frontend_egui/src/api");
                dirs.push("templates/frontend_egui");
            }
            super::Frontend::LeptosCsr | super::Frontend::LeptosSsr => {
            }
        }
    }

    for dir in dirs.iter() {
        fs::create_dir_all(project_dir.join(dir))?;
        println!("📁 Created directory: {}/{}", name, dir);
    }

    // Basic backend skeleton
    let mut main_rs_content = r#"use axum::{routing::get, Router};
use axum_extra::extract::Host;
use std::net::SocketAddr;
use std::path::PathBuf;
use rustls_acme::{caches::DirCache, AcmeConfig};
use tokio_stream::StreamExt;
use tower_http::services::{ServeDir, ServeFile};

#[tokio::main]
async fn main() {
    // Load configuration from environment variables
    let port = std::env::var("PORT").unwrap_or_else(|_| "3000".to_string()).parse::<u16>().unwrap();
    let https = std::env::var("HTTPS").unwrap_or_else(|_| "false".to_string()) == "true";
    let domain = std::env::var("DOMAIN").ok();
    let email = std::env::var("EMAIL").ok();
    let static_dir = std::env::var("STATIC_DIR").ok();

    let mut app = Router::new().route("/api/health", get(|| async { "Ferrum API is healthy" }));

    // Serve static files (SPA support)
    if let Some(dir) = static_dir {
        let path = PathBuf::from(dir);
        if path.exists() {
            let serve_dir = ServeDir::new(&path)
                .not_found_service(ServeFile::new(path.join("index.html")));
            app = app.fallback_service(serve_dir);
            println!("📂 Serving static files from {:?}", path);
        } else {
            println!("⚠️  Static directory {:?} does not exist", path);
        }
    } else {
         app = app.route("/", get(|| async { "Hello Ferrum" }));
    }

    if https {
        if let Some(domain) = domain {
            println!("🔒 Starting HTTPS server on port 443 for domain {}", domain);

            let state = AcmeConfig::new(vec![domain.clone()])
                .contact(email.iter().map(|e| format!("mailto:{}", e)))
                .cache_option(Some(DirCache::new("certs")))
                .directory_lets_encrypt(true)
                .state();

            let acceptor = state.axum_acceptor(state.default_rustls_config());

            tokio::spawn(async move {
                let mut state = state;
                loop {
                    match state.next().await.unwrap() {
                        Ok(ok) => println!("event: {:?}", ok),
                        Err(err) => println!("error: {:?}", err),
                    }
                }
            });

            let addr = SocketAddr::from(([0, 0, 0, 0], 443));
            let listener = axum_server::bind(addr).acceptor(acceptor);
            println!("🚀 HTTPS Server running on https://{}", domain);

            // Optional HTTP redirect
            tokio::spawn(async move {
                let redirect_app = Router::new().fallback(move |host: Host, uri: axum::http::Uri| async move {
                    let url = format!("https://{}{}", host.0, uri);
                    axum::response::Redirect::permanent(&url)
                });
                let addr = SocketAddr::from(([0, 0, 0, 0], 80));
                println!("↩️  Redirecting HTTP traffic from port 80 to HTTPS");
                axum_server::bind(addr)
                    .serve(redirect_app.into_make_service())
                    .await
                    .unwrap();
            });

            listener.serve(app.into_make_service()).await.unwrap();
        } else {
            eprintln!("❌ HTTPS enabled but DOMAIN env var is missing");
            std::process::exit(1);
        }
    } else {
        let addr = SocketAddr::from(([0, 0, 0, 0], port));
        println!("🚀 Backend running on {}", addr);
        axum_server::bind(addr)
            .serve(app.into_make_service())
            .await
            .unwrap();
    }
}
"#.to_string();

    if with_ai {
        main_rs_content = format!("{}\n{}",
            "#[cfg(feature = \"ai\")]\npub mod ai;\n",
            main_rs_content
        );
        // We might want to register routes here in the future, but for now just the mod declaration
    }

    fs::write(
        project_dir.join("backend/src/main.rs"),
        main_rs_content,
    )?;
    fs::write(
        project_dir.join("backend/tests/integration_test.rs"),
        r#"#[test]
fn test_hello_world() {
    assert_eq!(2 + 2, 4);
}
"#,
    )?;
    fs::write(
        project_dir.join("backend/Cargo.toml"),
        r#"[package]
name = "backend"
version = "0.1.0"
edition = "2021"
keywords = ["ferrum", "axum", "rust"]

[dependencies]
axum = "0.8"
tokio = { version = "1", features = ["full"] }
serde = { version = "1", features = ["derive"] }
embedded-hal = { version = "1", optional = true }
rppal = { version = "0.18", optional = true }
rumqttc = { version = "0.22", optional = true }
ethercat-rs = { version = "0.2", package = "ethercat_rs", optional = true }
axum-server = { version = "0.8", features = ["tls-rustls"] }
axum-extra = { version = "0.12", features = ["typed-header"] }
rustls-acme = { version = "0.15", features = ["axum"] }
tower-http = { version = "0.5", features = ["fs", "trace", "cors"] }
tokio-stream = "0.1"

[features]
default = []
hal = ["dep:embedded-hal"]
rppal = ["dep:rppal"]
mqtt = ["dep:rumqttc"]
ethercat = ["dep:ethercat-rs"]
"#,
    )?;

    // Create shared-models Cargo.toml for EGUI projects
    if !api_only && matches!(frontend, super::Frontend::Egui) {
        fs::write(
            project_dir.join("shared-models/Cargo.toml"),
            r#"[package]
name = "shared-models"
version = "0.1.0"
edition = "2021"

[dependencies]
serde = { version = "1.0", features = ["derive"] }
uuid = { version = "1.0", features = ["serde"] }
chrono = { version = "0.4", features = ["serde"] }
"#,
        )?;
        
        fs::write(
            project_dir.join("shared-models/src/lib.rs"),
            "// Shared models between backend and frontend\n",
        )?;
        println!("📄 Created shared-models crate");
    }

    if matches!(frontend, super::Frontend::LeptosCsr | super::Frontend::LeptosSsr) {
        fs::write(
            project_dir.join("Cargo.toml"),
            ""
        )?;
    }

    if !api_only && !nostarter {
        match frontend {
            super::Frontend::React => write_react_starter(&project_dir)?,
            super::Frontend::Egui => write_egui_starter(&project_dir)?,
            super::Frontend::LeptosCsr | super::Frontend::LeptosSsr => {
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
            include_str!("../../../../templates/backend/db/schema.rs.tera"),
        )?;
        fs::write(
            project_dir.join("templates/backend/db/models.rs.tera"),
            include_str!("../../../../templates/backend/db/models.rs.tera"),
        )?;
        fs::write(
            project_dir.join("templates/backend/db/mod.rs.tera"),
            include_str!("../../../../templates/backend/db/mod.rs.tera"),
        )?;

        // Copy optional seed data
        fs::create_dir_all(project_dir.join("templates/backend/db/seeds"))?;
        fs::write(
            project_dir.join("templates/backend/db/seeds/usuarios.sql"),
            include_str!("../../../../templates/backend/db/seeds/usuarios.sql"),
        )?;

        fs::create_dir_all(project_dir.join("backend/seeds"))?;
        fs::write(
            project_dir.join("backend/seeds/usuarios.sql"),
            include_str!("../../../../templates/backend/db/seeds/usuarios.sql"),
        )?;

        let mig_template_dir =
            project_dir.join("templates/backend/db/migrations/0001_create_usuarios");
        fs::create_dir_all(&mig_template_dir)?;
        fs::write(
            mig_template_dir.join("up.sql"),
            include_str!("../../../../templates/backend/db/migrations/0001_create_usuarios/up.sql"),
        )?;
        fs::write(
            mig_template_dir.join("down.sql"),
            include_str!("../../../../templates/backend/db/migrations/0001_create_usuarios/down.sql"),
        )?;

        let mig_dir = project_dir.join("backend/migrations/0001_create_usuarios");
        fs::create_dir_all(&mig_dir)?;
        fs::write(
            mig_dir.join("up.sql"),
            include_str!("../../../../templates/backend/db/migrations/0001_create_usuarios/up.sql"),
        )?;
        fs::write(
            mig_dir.join("down.sql"),
            include_str!("../../../../templates/backend/db/migrations/0001_create_usuarios/down.sql"),
        )?;

        // Create .env with database URL
        let db_url = match db_type {
            super::DbType::Postgres => "postgres://usuario:clave@localhost/ferrum_dev",
            super::DbType::Sqlite => "sqlite:data/ferrum_dev.db",
        };
        fs::write(
            project_dir.join(".env"),
            format!("DATABASE_URL={}\n", db_url),
        )?;

        // Create diesel.toml for CLI configuration
        fs::write(
            project_dir.join("diesel.toml"),
            "[print_schema]\nfile = \"src/schema.rs\"\n",
        )?;

        // Create basic Makefile with DB init commands
        let makefile_content = match db_type {
            super::DbType::Postgres => "db-init:\n\tdiesel setup\n\tdiesel migration generate create_usuarios\n\ntest:\n\tcd backend && cargo test\n",
            super::DbType::Sqlite => "db-init:\n\tdiesel setup\n\tdiesel migration generate create_usuarios\n\ntest:\n\tcd backend && cargo test\n",
        };
        fs::write(
            project_dir.join("Makefile"),
            makefile_content,
        )?;

        println!("📄 Added Diesel templates and .env file");
    }

    if with_auth {
        fs::create_dir_all(project_dir.join("templates/batteries/auth"))?;
        fs::write(
            project_dir.join("templates/batteries/auth/login_handler.rs.tera"),
            include_str!("../../../../templates/batteries/auth/login_handler.rs.tera"),
        )?;
        println!("📄 Added authentication templates");
    }

    if with_jobs {
        fs::create_dir_all(project_dir.join("templates/batteries/jobs"))?;
        fs::write(
            project_dir.join("templates/batteries/jobs/example_job.rs.tera"),
            include_str!("../../../../templates/batteries/jobs/example_job.rs.tera"),
        )?;
        println!("📄 Added job templates");
    }

    if with_uploads {
        fs::create_dir_all(project_dir.join("templates/batteries/uploads"))?;
        fs::write(
            project_dir.join("templates/batteries/uploads/backend/handlers/upload.rs.tera"),
            include_str!("../../../../templates/batteries/uploads/backend/handlers/upload.rs.tera"),
        )?;
        fs::write(
            project_dir.join("templates/batteries/uploads/backend/routes/uploads.rs.tera"),
            include_str!("../../../../templates/batteries/uploads/backend/routes/uploads.rs.tera"),
        )?;
        fs::write(
            project_dir
                .join("templates/batteries/uploads/frontend/components/FileDropzone.tsx.tera"),
            include_str!(
                "../../../../templates/batteries/uploads/frontend/components/FileDropzone.tsx.tera"
            ),
        )?;
        fs::write(
            project_dir.join("templates/batteries/uploads/frontend/hooks/useUploadFile.ts.tera"),
            include_str!("../../../../templates/batteries/uploads/frontend/hooks/useUploadFile.ts.tera"),
        )?;
        println!("📄 Added upload templates");
    }

    // Create docker-compose.yml
    let mut docker_compose = fs::File::create(project_dir.join("docker-compose.yml"))?;
    let mut docker_compose_content = include_str!("../../../../templates/docker-compose.yml").to_string();
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
        include_str!("../../../../templates/Dockerfile"),
    )?;
    println!("📄 Created Dockerfile");

    fs::write(
        project_dir.join("compose.prod.yaml"),
        include_str!("../../../../templates/compose.prod.yaml"),
    )?;
    println!("📄 Created compose.prod.yaml");

    if with_db {
        let dockerfile_path = project_dir.join("backend/Dockerfile");
        fs::create_dir_all(project_dir.join("backend"))?;
        let dockerfile_content = match db_type {
            super::DbType::Postgres => "FROM rust:latest\nRUN apt-get update && apt-get install -y build-essential pkg-config libssl-dev libpq-dev \\n+    && cargo install diesel_cli --no-default-features --features postgres\nWORKDIR /app\n",
            super::DbType::Sqlite => "FROM rust:latest\nRUN apt-get update && apt-get install -y build-essential pkg-config libsqlite3-dev \\n+    && cargo install diesel_cli --no-default-features --features sqlite\nWORKDIR /app\n",
        };
        fs::write(
            dockerfile_path,
            dockerfile_content,
        )?;
        println!("📄 Created backend/Dockerfile with diesel_cli");
    }

    // Create example grafo.yaml
    let mut example_yaml = fs::File::create(project_dir.join("gen/example.yaml"))?;
    let example_yaml_content = include_str!("../../../../gen/users.yaml");
    example_yaml.write_all(example_yaml_content.as_bytes())?;
    println!("📄 Created example grafo.yaml");

    if with_db || with_ai {
        let cargo_toml_path = project_dir.join("backend/Cargo.toml");
        fs::create_dir_all(project_dir.join("backend"))?;
        // toml 0.9+ (spec 1.1) split `Value` into "a single value expression"
        // and `Table` into "a whole document" — `Value::parse` no longer
        // accepts a multi-table document like a `Cargo.toml`. `Table` does.
        let mut cargo_toml: toml::Table = toml::from_str(&fs::read_to_string(&cargo_toml_path)?)?;
        let dependencies = cargo_toml["dependencies"].as_table_mut().unwrap();

        if with_db {
            let mut diesel_dependency = toml::map::Map::new();
            diesel_dependency.insert("version".to_string(), toml::Value::String("2.3".to_string()));
            let features = match db_type {
                super::DbType::Postgres => vec!["postgres", "r2d2"],
                super::DbType::Sqlite => vec!["sqlite", "r2d2"],
            };
            diesel_dependency.insert("features".to_string(), toml::Value::Array(features.into_iter().map(|s| toml::Value::String(s.to_string())).collect()));
            dependencies.insert(
                "diesel".to_string(),
                toml::Value::Table(diesel_dependency),
            );
            dependencies.insert(
                "dotenvy".to_string(),
                toml::Value::String("0.15".to_string()),
            );
        }

        if with_ai {
            let mut pgvector_dep = toml::map::Map::new();
            pgvector_dep.insert("version".to_string(), toml::Value::String("0.4".to_string()));
            pgvector_dep.insert("features".to_string(), toml::Value::Array(vec![toml::Value::String("diesel".to_string())]));

            dependencies.insert(
                "pgvector".to_string(),
                toml::Value::Table(pgvector_dep),
            );
            dependencies.insert(
                "reqwest".to_string(),
                toml::Value::String("0.12".to_string()),
            );
            dependencies.insert(
                "serde_json".to_string(),
                toml::Value::String("1.0".to_string()),
            );

            // Add ai feature — `cargo_toml` is itself the document's table now
            // (see the `toml::Table` note above), so no `.as_table_mut()` step.
            {
                let features_table = cargo_toml
                    .entry("features".to_string())
                    .or_insert(toml::Value::Table(toml::map::Map::new()));
                if let toml::Value::Table(f) = features_table {
                    f.insert("ai".to_string(), toml::Value::Array(vec![]));
                    // Add ai to default
                    if let Some(toml::Value::Array(default)) = f.get_mut("default") {
                        default.push(toml::Value::String("ai".to_string()));
                    } else {
                        f.insert("default".to_string(), toml::Value::Array(vec![toml::Value::String("ai".to_string())]));
                    }
                }
            }
        }

        fs::write(&cargo_toml_path, toml::to_string(&cargo_toml)?)?;
        println!("📄 Updated backend/Cargo.toml with dependencies");
    }

    // Create README.md
    let mut readme = fs::File::create(project_dir.join("README.md"))?;
    let frontend_section = if api_only {
        String::new()
    } else {
        match frontend {
            super::Frontend::React => "- `frontend/`: React frontend with TypeScript\n".to_string(),
            super::Frontend::Egui => "- `frontend_egui/`: EGUI native desktop frontend\n".to_string(),
            _ => "- `frontend/`: Frontend application\n".to_string(),
        }
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
    // Project-level frontend config.
    fs::write(dir.join("frontend/package.json"), include_str!("../../../../templates/frontend/package.json"))?;
    fs::write(dir.join("frontend/tsconfig.json"), include_str!("../../../../templates/frontend/tsconfig.json"))?;
    fs::write(dir.join("frontend/vite.config.ts"), include_str!("../../../../templates/frontend/vite.config.ts"))?;
    fs::write(dir.join("frontend/index.html"), include_str!("../../../../templates/frontend/index.html"))?;
    // Tailwind + shadcn/ui: the generated components and forms import these
    // primitives, so they have to exist in a freshly initialised project.
    fs::write(dir.join("frontend/tailwind.config.js"), include_str!("../../../../templates/frontend/tailwind.config.js"))?;
    fs::write(dir.join("frontend/postcss.config.js"), include_str!("../../../../templates/frontend/postcss.config.js"))?;
    fs::write(dir.join("frontend/src/index.css"), include_str!("../../../../templates/frontend/index.css"))?;
    fs::write(dir.join("frontend/src/App.tsx"), "export default function App() {\n  return <h1>Ferrum app ready!</h1>;\n}\n")?;
    fs::write(dir.join("frontend/src/main.tsx"), include_str!("../../../../templates/frontend/main.tsx"))?;
    // `lib/` and `components/ui/` are new directories, so create them first —
    // `fs::write` does not create parent directories.
    fs::create_dir_all(dir.join("frontend/src/lib"))?;
    fs::write(dir.join("frontend/src/lib/utils.ts"), include_str!("../../../../templates/frontend/lib/utils.ts"))?;
    fs::create_dir_all(dir.join("frontend/src/components/ui"))?;
    for (name, source) in [
        ("button.tsx", include_str!("../../../../templates/frontend/ui/button.tsx")),
        ("card.tsx", include_str!("../../../../templates/frontend/ui/card.tsx")),
        ("input.tsx", include_str!("../../../../templates/frontend/ui/input.tsx")),
        ("label.tsx", include_str!("../../../../templates/frontend/ui/label.tsx")),
        ("table.tsx", include_str!("../../../../templates/frontend/ui/table.tsx")),
        ("textarea.tsx", include_str!("../../../../templates/frontend/ui/textarea.tsx")),
    ] {
        fs::write(dir.join("frontend/src/components/ui").join(name), source)?;
    }
    Ok(())
}

fn write_egui_starter(dir: &Path) -> Result<()> {
    use std::fs;
    
    // Create Cargo.toml for EGUI frontend
    fs::write(
        dir.join("frontend_egui/Cargo.toml"),
        r#"[package]
name = "frontend_egui"
version = "0.1.0"
edition = "2021"

[dependencies]
eframe = "0.27"
egui = "0.27"
serde = { version = "1.0", features = ["derive"] }
serde_json = "1.0"
reqwest = { version = "0.11", features = ["json", "blocking"] }
tokio = { version = "1", features = ["rt", "rt-multi-thread"] }
anyhow = "1.0"
uuid = { version = "1.0", features = ["serde"] }
chrono = { version = "0.4", features = ["serde"] }

# Shared models from workspace
shared-models = { path = "../shared-models" }
"#,
    )?;

    // Create main.rs
    fs::write(
        dir.join("frontend_egui/src/main.rs"),
        r#"mod app;
mod state;
mod navigation;
mod views;
mod forms;
mod api;

use app::App;

fn main() -> Result<(), eframe::Error> {
    let options = eframe::NativeOptions {
        viewport: egui::ViewportBuilder::default()
            .with_inner_size([1280.0, 720.0]),
        ..Default::default()
    };
    
    eframe::run_native(
        "Ferrum App",
        options,
        Box::new(|cc| Box::new(App::new(cc))),
    )
}
"#,
    )?;

    // Create app.rs
    fs::write(
        dir.join("frontend_egui/src/app.rs"),
        r#"use crate::api::ApiClient;
use crate::navigation::View;
use crate::state::AppState;

pub struct App {
    state: AppState,
    current_view: View,
    api_client: ApiClient,
}

impl App {
    pub fn new(_cc: &eframe::CreationContext<'_>) -> Self {
        Self {
            state: AppState::new(),
            current_view: View::Home,
            api_client: ApiClient::new("http://localhost:3000".to_string()),
        }
    }

    fn render_navigation(&mut self, ui: &mut egui::Ui) {
        ui.horizontal(|ui| {
            ui.heading("Ferrum App");
            ui.separator();
            
            for view in View::all() {
                if ui.button(view.name()).clicked() {
                    self.current_view = *view;
                }
            }
        });
        ui.separator();
    }

    fn render_current_view(&mut self, ui: &mut egui::Ui) {
        match self.current_view {
            View::Home => {
                ui.heading("Welcome to Ferrum");
                ui.label("Your EGUI application is ready!");
            }
        }
    }
}

impl eframe::App for App {
    fn update(&mut self, ctx: &egui::Context, _frame: &mut eframe::Frame) {
        egui::CentralPanel::default().show(ctx, |ui| {
            self.render_navigation(ui);
            self.render_current_view(ui);
        });
    }
}
"#,
    )?;

    // Create state.rs
    fs::write(
        dir.join("frontend_egui/src/state.rs"),
        r#"#[derive(Default)]
pub struct AppState {
    pub token: Option<String>,
}

impl AppState {
    pub fn new() -> Self {
        Self::default()
    }

    pub fn is_authenticated(&self) -> bool {
        self.token.is_some()
    }

    pub fn logout(&mut self) {
        self.token = None;
    }
}
"#,
    )?;

    // Create navigation.rs
    fs::write(
        dir.join("frontend_egui/src/navigation.rs"),
        r#"#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum View {
    Home,
}

impl View {
    pub fn all() -> &'static [View] {
        &[View::Home]
    }

    pub fn name(&self) -> &'static str {
        match self {
            View::Home => "Home",
        }
    }

    pub fn requires_auth(&self) -> bool {
        false
    }
}
"#,
    )?;

    // Create views/mod.rs
    fs::write(
        dir.join("frontend_egui/src/views/mod.rs"),
        "// Generated views will be added here\n",
    )?;

    // Create forms/mod.rs
    fs::write(
        dir.join("frontend_egui/src/forms/mod.rs"),
        "// Generated forms will be added here\n",
    )?;

    // Create api/mod.rs
    fs::write(
        dir.join("frontend_egui/src/api/mod.rs"),
        r#"mod client;

pub use client::ApiClient;
"#,
    )?;

    // Create api/client.rs
    fs::write(
        dir.join("frontend_egui/src/api/client.rs"),
        r#"use anyhow::Result;
use serde::{Deserialize, Serialize};

pub struct ApiClient {
    base_url: String,
    client: reqwest::blocking::Client,
}

impl ApiClient {
    pub fn new(base_url: String) -> Self {
        Self {
            base_url,
            client: reqwest::blocking::Client::new(),
        }
    }

    pub fn get<T: for<'de> Deserialize<'de>>(&self, path: &str) -> Result<T> {
        let url = format!("{}{}", self.base_url, path);
        let response = self.client.get(&url).send()?;
        let data = response.json()?;
        Ok(data)
    }

    pub fn post<T: Serialize, R: for<'de> Deserialize<'de>>(
        &self,
        path: &str,
        body: &T,
    ) -> Result<R> {
        let url = format!("{}{}", self.base_url, path);
        let response = self.client.post(&url).json(body).send()?;
        let data = response.json()?;
        Ok(data)
    }
}
"#,
    )?;

    println!("📄 Created EGUI frontend structure");
    Ok(())
}

