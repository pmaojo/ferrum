use anyhow::Result;
use clap::{Parser, Subcommand};
use std::path::PathBuf;

#[derive(Parser)]
#[command(name = "ferrum")]
#[command(about = "AI-first scaffolding system for full-stack applications", long_about = None)]
pub struct Cli {
    #[command(subcommand)]
    pub command: Commands,
}

#[derive(Subcommand)]
pub enum Commands {
    /// Compile a grafo.yaml file into code
    Compile {
        /// Path to the grafo.yaml file
        #[arg(value_name = "FILE")]
        file: PathBuf,

        /// Output directory for generated code
        #[arg(short, long, value_name = "DIR")]
        output: Option<PathBuf>,

        /// Templates directory
        #[arg(short, long, value_name = "DIR")]
        templates: Option<PathBuf>,
    },

    /// Generate a grafo.yaml file from a prompt
    Prompt {
        /// Prompt text
        #[arg(value_name = "TEXT")]
        text: String,

        /// Output file for the generated grafo.yaml
        #[arg(short, long, value_name = "FILE")]
        output: Option<PathBuf>,
    },

    /// Generate a shared component from a prompt
    Component {
        /// Prompt text
        #[arg(value_name = "TEXT")]
        text: String,

        /// Output file for the generated component YAML
        #[arg(short, long, value_name = "FILE")]
        output: Option<PathBuf>,
    },

    /// Generate a usecase YAML from a prompt
    Usecase {
        /// Prompt text
        #[arg(value_name = "TEXT")]
        text: String,

        /// Output file for the generated YAML
        #[arg(short, long, value_name = "FILE")]
        output: Option<PathBuf>,
    },

    /// Generate a skeleton usecase YAML
    GenerateUsecase {
        /// Name of the usecase in PascalCase
        #[arg(value_name = "NAME")]
        name: String,

        /// Output file for the generated YAML
        #[arg(short, long, value_name = "FILE")]
        output: Option<PathBuf>,
    },

    /// Analyze a DSL YAML file for cycles and bottlenecks
    Analyze {
        /// Path to the grafo.yaml file
        #[arg(value_name = "FILE")]
        file: PathBuf,

        /// Output machine readable JSON
        #[arg(long)]
        json: bool,

        /// Threshold for bottleneck detection
        #[arg(long, value_name = "N", default_value_t = 3)]
        bottleneck: usize,
    },

    /// Start development environment
    Dev {
        /// Run using docker-compose instead of local processes
        #[arg(long)]
        docker: bool,

        /// Include graph database (Neo4j)
        #[arg(long)]
        with_graph: bool,

        /// Include AI/LLM service (Ollama)
        #[arg(long)]
        with_ai: bool,
    },

    /// Initialize a new Ferrum project
    Init {
        /// Project name
        #[arg(value_name = "NAME")]
        name: String,

        /// Include graph database support
        #[arg(long)]
        with_graph: bool,

        /// Include AI/LLM integration
        #[arg(long)]
        with_ai: bool,

        /// Include Diesel ORM setup
        #[arg(long)]
        with_db: bool,

        /// Include authentication templates
        #[arg(long)]
        with_auth: bool,

        /// Include background job templates
        #[arg(long)]
        with_jobs: bool,

        /// Include file upload templates
        #[arg(long)]
        with_uploads: bool,

        /// Backend only project without frontend
        #[arg(long)]
        api_only: bool,

        /// Interactive mode
        #[arg(short, long)]
        interactive: bool,
    },

    /// Generate a DOT graph visualization from a DSL file
    Graph {
        /// Path to the grafo.yaml file
        #[arg(value_name = "FILE")]
        file: PathBuf,

        /// Output dot file path
        #[arg(short, long, value_name = "FILE", default_value = "graph.dot")]
        output: PathBuf,
    },

    /// Sync a grafo.yaml file to Neo4j
    Sync {
        /// Path to the grafo.yaml file
        #[arg(value_name = "FILE")]
        file: PathBuf,

        /// Neo4j connection URI
        #[arg(long, default_value = "bolt://localhost:7687")]
        uri: String,

        /// Neo4j username
        #[arg(long, default_value = "neo4j")]
        user: String,

        /// Neo4j password
        #[arg(long, default_value = "test")]
        password: String,
    },

    /// Run Diesel database migrations
    Migrate {},
    /// Validate configuration and environment
    Doctor {},
    Add {
        #[arg(value_name = "PLUGIN")]
        plugin: String,
    },
    Remove {
        #[arg(value_name = "PLUGIN")]
        plugin: String,
    },
    List {},
    /// Explain a DSL file after applying installed plugins
    Explain {
        #[arg(value_name = "FILE")]
        file: PathBuf,
    },
    /// Show documentation for a plugin
    Docs {
        #[arg(value_name = "PLUGIN")]
        plugin: String,
    },
    /// Extract translatable messages and generate an i18n file
    I18n {
        /// Directory to scan
        #[arg(value_name = "DIR", default_value = ".")]
        dir: PathBuf,

        /// Output TypeScript file
        #[arg(
            short,
            long,
            value_name = "FILE",
            default_value = "frontend/src/i18n.ts"
        )]
        output: PathBuf,
    },

    /// Fill AI markers in generated code using GraphRAG
    FillTodos {
        /// Directory to process
        #[arg(value_name = "DIR", default_value = "gen")]
        dir: PathBuf,
    },

    /// Chat with the AI coordinator team
    AiTeam {
        /// Prompt text
        #[arg(value_name = "TEXT")]
        text: String,
    },

    /// Generate an execution flow report for a DSL file
    Flow {
        /// Path to the grafo.yaml file
        #[arg(value_name = "FILE")]
        file: PathBuf,
    },

    /// Build the backend for a specific target
    Build {
        /// Target triple (e.g. x86_64-unknown-linux-gnu)
        #[arg(short, long, value_name = "TRIPLE")]
        target: Option<String>,
    },
}

/// Compile a `grafo.yaml` architecture file into source code.
pub fn compile(file: PathBuf, output: Option<PathBuf>, templates: Option<PathBuf>) -> Result<()> {
    let output_dir = output.unwrap_or_else(|| PathBuf::from("."));
    let templates_dir = templates.unwrap_or_else(|| PathBuf::from("templates"));
    let plugins = load_plugins()?;

    // Try new DSL format first, fall back to legacy format
    if let Ok(mut project) = ferrum_compiler::parse_dsl_yaml(&file) {
        plugins.extend_dsl_all(&mut project)?;
        let modules = ferrum_compiler::project_to_modules(&mut project);
        ferrum_compiler::validate_modules(&modules)?;
        ferrum_compiler::validate_features(&project, &modules)?;
        ferrum_compiler::validate_validations(&project, &modules)?;
        let mut generator =
            ferrum_compiler::Generator::new(templates_dir.clone(), output_dir.clone())?;
        generator.set_modules(modules.clone());
        for m in &modules {
            ferrum_compiler::validate_module(m)?;
            generator.generate(m)?;
        }
        let paths = ferrum_compiler::ProjectPaths::new(&output_dir);
        ferrum_compiler::compile_dsl(&project, &paths)?;
    } else {
        let module = ferrum_compiler::parse_yaml(&file)?;
        ferrum_compiler::validate_module(&module)?;

        let generator = ferrum_compiler::Generator::new(templates_dir, output_dir.clone())?;
        generator.generate(&module)?;
    }

    println!("✅ Successfully compiled {}", file.display());
    plugins.compile_all()?;
    Ok(())
}

/// Generate a `grafo.yaml` file from a free form prompt.
pub fn prompt(text: String, output: Option<PathBuf>) -> Result<()> {
    use crate::config::LlmConfig;
    use reqwest::blocking::Client;
    use std::fs;
    use std::path::PathBuf;

    println!("🤖 AI Architecture Generation");
    println!("━━━━━━━━━━━━━━━━━━━━━━━━━━━━");
    println!("Prompt: {}", text);
    println!();

    // Determine model from env or llm-config.yaml
    let cfg_model = LlmConfig::load().and_then(|c| c.model);
    let model = std::env::var("MODEL")
        .ok()
        .or(cfg_model)
        .unwrap_or_else(|| "openai".to_string());

    // Call Python AI service
    let client = Client::new();
    let response = client
        .post("http://localhost:8000/generate-yaml")
        .json(&serde_json::json!({ "text": text, "model": model }))
        .send()?;

    let yaml = response
        .json::<serde_json::Value>()?
        .get("yaml")
        .and_then(|v| v.as_str())
        .unwrap_or("module: generated\nnodes: []")
        .to_string();

    let output_path = output.unwrap_or_else(|| PathBuf::from("gen/generated.yaml"));
    fs::create_dir_all(output_path.parent().unwrap())?;
    fs::write(&output_path, yaml)?;

    println!(
        "✅ Architecture graph generated at: {}",
        output_path.display()
    );
    println!(
        "ℹ️  Run 'ferrum compile {}' to generate code from this architecture",
        output_path.display()
    );

    Ok(())
}

/// Generate a component YAML snippet from a free form prompt.
pub fn component_prompt(text: String, output: Option<PathBuf>) -> Result<()> {
    use crate::config::LlmConfig;
    use reqwest::blocking::Client;
    use std::fs;
    use std::path::PathBuf;

    println!("🤖 AI Component Generation");
    println!("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━");
    println!("Prompt: {}", text);
    println!();

    let cfg_model = LlmConfig::load().and_then(|c| c.model);
    let model = std::env::var("MODEL")
        .ok()
        .or(cfg_model)
        .unwrap_or_else(|| "openai".to_string());

    let client = Client::new();
    let response = client
        .post("http://localhost:8000/generate-component")
        .json(&serde_json::json!({ "text": text, "model": model }))
        .send()?;

    let yaml = response
        .json::<serde_json::Value>()?
        .get("yaml")
        .and_then(|v| v.as_str())
        .unwrap_or("components: []")
        .to_string();

    let output_path = output.unwrap_or_else(|| PathBuf::from("gen/component.yaml"));
    fs::create_dir_all(output_path.parent().unwrap())?;
    fs::write(&output_path, yaml)?;

    println!("✅ Component YAML generated at: {}", output_path.display());

    Ok(())
}

/// Generate a usecase YAML snippet from a free form prompt.
pub fn usecase_prompt(text: String, output: Option<PathBuf>) -> Result<()> {
    use crate::config::LlmConfig;
    use reqwest::blocking::Client;
    use std::fs;
    use std::path::PathBuf;

    println!("🤖 Generating usecase from prompt...");
    println!("━━━━━━━━━━━━━━━━━━━━━━━━━━━");
    println!("Prompt: {}", text);
    println!();

    let cfg_model = LlmConfig::load().and_then(|c| c.model);
    let model = std::env::var("MODEL")
        .ok()
        .or(cfg_model)
        .unwrap_or_else(|| "openai".to_string());

    let client = Client::new();
    let response = client
        .post("http://localhost:8000/generate-usecase")
        .json(&serde_json::json!({ "text": text, "model": model }))
        .send()?;

    let yaml = response
        .json::<serde_json::Value>()?
        .get("yaml")
        .and_then(|v| v.as_str())
        .unwrap_or("")
        .to_string();

    let output_path = output.unwrap_or_else(|| PathBuf::from("gen/usecase.yaml"));
    fs::create_dir_all(output_path.parent().unwrap())?;
    fs::write(&output_path, yaml)?;

    println!("✅ Usecase YAML generated at: {}", output_path.display());

    Ok(())
}

/// Generate a simple usecase YAML snippet.
pub fn generate_usecase(name: String, output: Option<PathBuf>) -> Result<()> {
    use std::fs;
    use std::path::PathBuf;

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

/// Start the local development environment using Docker.
pub fn dev(docker: bool, with_graph: bool, with_ai: bool) -> Result<()> {
    use std::path::Path;
    use std::process::{Command, Stdio};
    use std::sync::atomic::{AtomicBool, Ordering};
    use std::sync::Arc;

    println!("🚀 Starting Ferrum development environment");
    println!("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━");

    let frontend_exists = Path::new("frontend").exists();

    if !docker {
        // Run local cargo and vite processes in parallel
        // Compile all YAML files first to ensure routes and types are up to date
        if let Ok(entries) = std::fs::read_dir("gen") {
            for entry in entries.flatten() {
                if entry.path().extension().and_then(|s| s.to_str()) == Some("yaml") {
                    let _ = compile(entry.path(), None, None);
                }
            }
        }

        let mut backend = Command::new("cargo")
            .arg("run")
            .arg("--manifest-path")
            .arg("backend/Cargo.toml")
            .stdout(Stdio::inherit())
            .stderr(Stdio::inherit())
            .spawn()?;
        let mut frontend = if frontend_exists {
            Some(
                Command::new("npm")
                    .args(["run", "dev", "--prefix", "frontend"])
                    .stdout(Stdio::inherit())
                    .stderr(Stdio::inherit())
                    .spawn()?,
            )
        } else {
            None
        };

        let running = Arc::new(AtomicBool::new(true));
        let r = running.clone();
        ctrlc::set_handler(move || {
            r.store(false, Ordering::SeqCst);
        })?;

        while running.load(Ordering::SeqCst) {
            std::thread::sleep(std::time::Duration::from_millis(500));
            if backend.try_wait()?.is_some()
                || frontend.as_mut().and_then(|f| f.try_wait().ok()).is_some()
            {
                running.store(false, Ordering::SeqCst);
            }
        }

        let _ = backend.kill();
        if let Some(mut f) = frontend {
            let _ = f.kill();
        }
        return Ok(());
    }

    // Create a docker-compose command with the appropriate services
    let mut services = vec!["backend", "db"];
    if frontend_exists {
        services.insert(1, "frontend");
    }

    if with_graph {
        services.push("graphdb");
        println!("🔍 Including graph database (Neo4j)");
    }

    if with_ai {
        services.push("llm");
        println!("🧠 Including AI/LLM service (Ollama)");
    }

    println!("⚙️  Starting services: {}", services.join(", "));
    println!();

    // Build the docker-compose command
    let services_arg = services.join(" ");
    let docker_compose_cmd = format!("docker-compose up {}", services_arg);

    println!("🚀 Launching development environment...");
    println!("💡 Press Ctrl+C to stop all services");
    println!();

    // Execute the command
    let status = Command::new("sh")
        .arg("-c")
        .arg(&docker_compose_cmd)
        .status()?;

    if !status.success() {
        println!("❌ Failed to start development environment");
        return Err(anyhow::anyhow!("Docker command failed"));
    }

    Ok(())
}

/// Scaffold a new Ferrum project on disk.
pub fn init(
    name: String,
    mut with_graph: bool,
    mut with_ai: bool,
    mut with_db: bool,
    mut with_auth: bool,
    mut with_jobs: bool,
    mut with_uploads: bool,
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
        dirs.push("frontend/src");
        dirs.push("templates/frontend");
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
"#,
    )?;

    if !api_only {
        // Basic frontend skeleton using Vite + React
        fs::write(
            project_dir.join("frontend/package.json"),
            r#"{
  "name": "frontend",
  "version": "0.0.0",
  "private": true,
  "scripts": {
    "dev": "vite",
    "build": "vite build",
    "preview": "vite preview"
  },
  "dependencies": {
    "react": "^18.2.0",
    "react-dom": "^18.2.0"
  },
  "devDependencies": {
    "@vitejs/plugin-react": "^3.0.0",
    "typescript": "^5.0.0",
    "vite": "^5.0.0"
  }
}
"#,
        )?;
        fs::write(
            project_dir.join("frontend/tsconfig.json"),
            r#"{
  "compilerOptions": {
    "target": "ESNext",
    "module": "ESNext",
    "jsx": "react-jsx",
    "strict": true,
    "moduleResolution": "bundler",
    "esModuleInterop": true,
    "skipLibCheck": true
  },
  "include": ["src"]
}
"#,
        )?;
        fs::write(
            project_dir.join("frontend/vite.config.ts"),
            r#"import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';

export default defineConfig({
  plugins: [react()],
});
"#,
        )?;
        fs::write(
            project_dir.join("frontend/index.html"),
            r#"<!doctype html>
<html lang=\"en\">
  <head>
    <meta charset=\"UTF-8\" />
    <meta name=\"viewport\" content=\"width=device-width, initial-scale=1.0\" />
    <title>Ferrum App</title>
  </head>
  <body>
    <div id=\"root\"></div>
    <script type=\"module\" src=\"/src/main.tsx\"></script>
  </body>
</html>
"#,
        )?;
        fs::write(project_dir.join("frontend/src/index.css"), "")?;
        fs::write(
            project_dir.join("frontend/src/App.tsx"),
            "export default function App() {\n  return <h1>Ferrum app ready!</h1>;\n}\n",
        )?;
        fs::write(
            project_dir.join("frontend/src/main.tsx"),
            r#"import React from 'react';
import ReactDOM from 'react-dom/client';
import App from './App';
import './index.css';

ReactDOM.createRoot(document.getElementById('root')!).render(
  <React.StrictMode>
    <App />
  </React.StrictMode>
);
"#,
        )?;
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
            include_str!("../../templates/backend/db/schema.rs.tera"),
        )?;
        fs::write(
            project_dir.join("templates/backend/db/models.rs.tera"),
            include_str!("../../templates/backend/db/models.rs.tera"),
        )?;
        fs::write(
            project_dir.join("templates/backend/db/mod.rs.tera"),
            include_str!("../../templates/backend/db/mod.rs.tera"),
        )?;

        // Copy optional seed data
        fs::create_dir_all(project_dir.join("templates/backend/db/seeds"))?;
        fs::write(
            project_dir.join("templates/backend/db/seeds/usuarios.sql"),
            include_str!("../../templates/backend/db/seeds/usuarios.sql"),
        )?;

        fs::create_dir_all(project_dir.join("backend/seeds"))?;
        fs::write(
            project_dir.join("backend/seeds/usuarios.sql"),
            include_str!("../../templates/backend/db/seeds/usuarios.sql"),
        )?;

        let mig_template_dir =
            project_dir.join("templates/backend/db/migrations/0001_create_usuarios");
        fs::create_dir_all(&mig_template_dir)?;
        fs::write(
            mig_template_dir.join("up.sql"),
            include_str!("../../templates/backend/db/migrations/0001_create_usuarios/up.sql"),
        )?;
        fs::write(
            mig_template_dir.join("down.sql"),
            include_str!("../../templates/backend/db/migrations/0001_create_usuarios/down.sql"),
        )?;

        let mig_dir = project_dir.join("backend/migrations/0001_create_usuarios");
        fs::create_dir_all(&mig_dir)?;
        fs::write(
            mig_dir.join("up.sql"),
            include_str!("../../templates/backend/db/migrations/0001_create_usuarios/up.sql"),
        )?;
        fs::write(
            mig_dir.join("down.sql"),
            include_str!("../../templates/backend/db/migrations/0001_create_usuarios/down.sql"),
        )?;

        // Create .env with database URL
        fs::write(
            project_dir.join(".env"),
            "DATABASE_URL=postgres://usuario:clave@localhost/ferrus_dev\n",
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
            include_str!("../../templates/batteries/auth/login_handler.rs.tera"),
        )?;
        println!("📄 Added authentication templates");
    }

    if with_jobs {
        fs::create_dir_all(project_dir.join("templates/batteries/jobs"))?;
        fs::write(
            project_dir.join("templates/batteries/jobs/example_job.rs.tera"),
            include_str!("../../templates/batteries/jobs/example_job.rs.tera"),
        )?;
        println!("📄 Added job templates");
    }

    if with_uploads {
        fs::create_dir_all(project_dir.join("templates/batteries/uploads"))?;
        fs::write(
            project_dir.join("templates/batteries/uploads/backend/handlers/upload.rs.tera"),
            include_str!("../../templates/batteries/uploads/backend/handlers/upload.rs.tera"),
        )?;
        fs::write(
            project_dir.join("templates/batteries/uploads/backend/routes/uploads.rs.tera"),
            include_str!("../../templates/batteries/uploads/backend/routes/uploads.rs.tera"),
        )?;
        fs::write(
            project_dir
                .join("templates/batteries/uploads/frontend/components/FileDropzone.tsx.tera"),
            include_str!(
                "../../templates/batteries/uploads/frontend/components/FileDropzone.tsx.tera"
            ),
        )?;
        fs::write(
            project_dir.join("templates/batteries/uploads/frontend/hooks/useUploadFile.ts.tera"),
            include_str!("../../templates/batteries/uploads/frontend/hooks/useUploadFile.ts.tera"),
        )?;
        println!("📄 Added upload templates");
    }

    // Create docker-compose.yml
    let mut docker_compose = fs::File::create(project_dir.join("docker-compose.yml"))?;
    let mut docker_compose_content = include_str!("../../templates/docker-compose.yml").to_string();
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
    let example_yaml_content = include_str!("../../gen/users.yaml");
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
    let plugins = load_plugins()?;
    plugins.init_all()?;
    println!("📂 Project location: {}", project_dir.display());
    println!();
    println!("Next steps:");
    println!("  1. cd {}", name);
    println!("  2. ferrum compile gen/example.yaml");
    println!("  3. ferrum dev");

    Ok(())
}

/// Synchronize a `grafo.yaml` file with a Neo4j instance.
pub fn sync(file: PathBuf, uri: String, user: String, password: String) -> Result<()> {
    use neo4rs::Graph;

    let module = ferrum_compiler::parse_yaml(&file)?;
    ferrum_compiler::validate_module(&module)?;
    let rt = tokio::runtime::Runtime::new()?;
    rt.block_on(async {
        let graph = Graph::new(uri.clone(), user.clone(), password.clone())?;
        ferrum_engine::sync_ast_to_graph(&module, &graph).await?;
        Ok::<_, anyhow::Error>(())
    })?;

    println!("✅ Synced {} to {}", file.display(), uri);
    Ok(())
}

/// Run Diesel database migrations using `diesel_migrations`.
pub fn migrate() -> Result<()> {
    use diesel::prelude::*;
    use diesel_migrations::{FileBasedMigrations, MigrationHarness};

    dotenvy::dotenv().ok();
    let database_url = std::env::var("DATABASE_URL")?;
    let mut conn = PgConnection::establish(&database_url)?;
    let migrations = FileBasedMigrations::find_migrations_directory()?;
    conn.run_pending_migrations(migrations)
        .map_err(|e| anyhow::anyhow!(e))?;

    println!("✅ Database migrations applied");
    Ok(())
}

/// Validate the local environment and configuration
pub fn doctor() -> Result<()> {
    use std::fs;
    println!("🔎 Running ferrum doctor...");
    let env_path = PathBuf::from(".env");
    if !env_path.exists() {
        println!("⚠️  .env file not found");
        return Ok(());
    }
    let contents = fs::read_to_string(&env_path)?;
    let mut ok = true;
    for key in [
        "JWT_SECRET",
        "GOOGLE_CLIENT_ID",
        "GOOGLE_CLIENT_SECRET",
        "GITHUB_CLIENT_ID",
        "GITHUB_CLIENT_SECRET",
    ] {
        let value = contents
            .lines()
            .find(|l| l.starts_with(key))
            .and_then(|l| l.splitn(2, '=').nth(1))
            .map(|v| v.trim())
            .unwrap_or("");
        if value.is_empty() {
            println!("⚠️  {key} is missing or empty in .env");
            ok = false;
        }
    }
    if ok {
        println!("✅ .env looks good");
    }
    Ok(())
}

/// Add a plugin to the local .ferrum/plugins list.
pub fn add_plugin(plugin: String) -> Result<()> {
    use std::fs::{self, OpenOptions};
    use std::io::Write;
    use std::path::Path;
    use std::process::Command;

    let dir = PathBuf::from(".ferrum");
    fs::create_dir_all(&dir)?;
    let file_path = dir.join("plugins.txt");
    let mut plugins = if file_path.exists() {
        fs::read_to_string(&file_path)?
            .lines()
            .map(|s| s.to_string())
            .collect::<Vec<_>>()
    } else {
        Vec::new()
    };

    let mut entry = plugin.clone();

    if plugin.starts_with("http") || (plugin.contains('/') && !Path::new(&plugin).exists()) {
        // Install from a remote git repository
        let repo_url = if plugin.starts_with("http") {
            plugin.clone()
        } else {
            format!("https://github.com/{}.git", plugin)
        };
        let repo_name = plugin.split('/').last().unwrap().trim_end_matches(".git");
        let dest = dir.join(repo_name);
        if !dest.exists() {
            println!("📥 Cloning {repo_url}...");
            let status = Command::new("git")
                .arg("clone")
                .arg(&repo_url)
                .arg(&dest)
                .status()?;
            if !status.success() {
                println!("Failed to clone repository");
            }
        }
        entry = dest.to_string_lossy().into_owned();
    } else if Path::new(&plugin).exists() {
        // Local path
        entry = std::fs::canonicalize(&plugin)?
            .to_string_lossy()
            .into_owned();
    }

    if !plugins.contains(&entry) {
        plugins.push(entry.clone());
        let mut f = OpenOptions::new()
            .create(true)
            .write(true)
            .truncate(true)
            .open(&file_path)?;
        writeln!(f, "{}", plugins.join("\n"))?;
        println!("✅ Added plugin: {}", entry);

        // Automatically compile if Cargo.toml exists
        let cargo_path = Path::new(&entry).join("Cargo.toml");
        if cargo_path.exists() {
            println!("🔨 Building plugin...");
            let status = Command::new("cargo")
                .arg("build")
                .arg("--release")
                .current_dir(&entry)
                .status()?;
            if status.success() {
                println!("✅ Plugin compiled");
                // Show SHA256 of compiled library if plugin.toml defines it
                let meta = Path::new(&entry).join("plugin.toml");
                if let Ok(meta) = ferrum_engine::plugins::PluginMetadata::from_file(&meta) {
                    let lib_path = Path::new(&entry).join(&meta.library);
                    if lib_path.exists() {
                        if let Ok(bytes) = std::fs::read(&lib_path) {
                            use sha2::{Digest, Sha256};
                            let hash = Sha256::digest(&bytes);
                            println!("🔑 SHA256: {:x}", hash);
                        }
                    }
                }
            } else {
                println!("⚠️ Failed to compile plugin");
            }
        } else {
            let meta = Path::new(&entry).join("plugin.toml");
            if meta.exists() {
                println!("⚠️ Using precompiled plugin binary. Ensure you trust the source.");
            }
        }

        // show docs if available
        if let Ok(_) = plugin_docs(entry.clone()) {}
    } else {
        println!("Plugin '{}' already added", entry);
    }
    Ok(())
}

/// Remove a plugin from the .ferrum/plugins list.
pub fn remove_plugin(plugin: String) -> Result<()> {
    use std::fs;

    let file_path = PathBuf::from(".ferrum/plugins.txt");
    if !file_path.exists() {
        println!("No plugins installed.");
        return Ok(());
    }

    let mut plugins: Vec<String> = fs::read_to_string(&file_path)?
        .lines()
        .map(|s| s.to_string())
        .collect();

    if let Some(pos) = plugins.iter().position(|p| p == &plugin) {
        plugins.remove(pos);
        if plugins.is_empty() {
            fs::remove_file(&file_path)?;
        } else {
            fs::write(&file_path, plugins.join("\n"))?;
        }
        println!("✅ Removed plugin: {}", plugin);
    } else {
        println!("Plugin '{}' not found", plugin);
    }
    Ok(())
}

/// List installed plugins from .ferrum/plugins.
pub fn list_plugins() -> Result<()> {
    use std::fs;
    let file_path = PathBuf::from(".ferrum/plugins.txt");
    if file_path.exists() {
        let contents = fs::read_to_string(file_path)?;
        if contents.trim().is_empty() {
            println!("No plugins installed.");
        } else {
            println!("Installed plugins:");
            for p in contents.lines() {
                println!("- {}", p);
            }
        }
    } else {
        println!("No plugins installed.");
    }
    Ok(())
}

/// Explain the final DSL after applying all installed plugins.
pub fn explain(file: PathBuf) -> Result<()> {
    let mut dsl = ferrum_compiler::parse_dsl_yaml(&file)?;
    let plugins = load_plugins()?;
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

/// Show documentation for a plugin if available.
pub fn plugin_docs(plugin: String) -> Result<()> {
    use std::fs;

    let name = plugin
        .split('/')
        .last()
        .unwrap_or(&plugin)
        .trim_end_matches(".git");

    // First try built-in docs
    let builtin = PathBuf::from(format!("docs/plugins/{name}.md"));
    if builtin.exists() {
        let contents = fs::read_to_string(builtin)?;
        println!("{}", contents);
        return Ok(());
    }

    // Then check installed plugin directories
    let plugins_file = PathBuf::from(".ferrum/plugins.txt");
    if plugins_file.exists() {
        let list = fs::read_to_string(&plugins_file)?;
        for line in list.lines() {
            let path = PathBuf::from(line.trim());
            let dir_name = path
                .file_name()
                .map(|s| s.to_string_lossy())
                .unwrap_or_default();
            if dir_name == name || line.trim() == plugin {
                let readme = path.join("README.md");
                if readme.exists() {
                    let contents = fs::read_to_string(readme)?;
                    println!("{}", contents);
                    return Ok(());
                }
            }
        }
    }

    // Finally, allow passing a direct path
    let direct = PathBuf::from(&plugin).join("README.md");
    if direct.exists() {
        let contents = fs::read_to_string(direct)?;
        println!("{}", contents);
        return Ok(());
    }

    println!("No docs found for {plugin}");
    Ok(())
}

/// Extract translatable strings from templates and YAML files
pub fn extract_i18n(dir: PathBuf, output: PathBuf) -> Result<()> {
    use regex::Regex;
    use std::collections::BTreeSet;
    use std::fs;
    use walkdir::WalkDir;

    let text_re = Regex::new(r">([^<]*[A-Za-z][^<]*)<")?;
    let placeholder_re = Regex::new(r#"placeholder=\"([^\"]+)\""#)?;
    let mut messages: BTreeSet<String> = BTreeSet::new();

    for entry in WalkDir::new(&dir).into_iter().filter_map(Result::ok) {
        let path = entry.path();
        if let Some(ext) = path.extension().and_then(|s| s.to_str()) {
            if ext == "tera" || ext == "yaml" {
                if let Ok(contents) = fs::read_to_string(path) {
                    for cap in text_re.captures_iter(&contents) {
                        messages.insert(cap[1].trim().to_string());
                    }
                    for cap in placeholder_re.captures_iter(&contents) {
                        messages.insert(cap[1].trim().to_string());
                    }
                }
            }
        }
    }

    let mut out = String::from("export const messages = {\n");
    for msg in &messages {
        let esc = msg.replace('"', "\\\"");
        out.push_str(&format!("  \"{}\": \"{}\",\n", esc, esc));
    }
    out.push_str("} as const;\n");

    if let Some(parent) = output.parent() {
        fs::create_dir_all(parent)?;
    }
    fs::write(&output, out)?;
    println!(
        "✅ Wrote {} messages to {}",
        messages.len(),
        output.display()
    );
    Ok(())
}

/// Generate a simple GraphViz DOT file from a DSL YAML architecture.
pub fn generate_graph(file: PathBuf, output: PathBuf) -> Result<()> {
    use std::fs;

    let module = ferrum_compiler::parse_yaml(&file)?;
    let mut dot = String::from("digraph Ferrum {\n");
    for node in &module.nodes {
        dot.push_str(&format!(
            "    {} [label=\"{} ({:?})\"];\n",
            node.id, node.id, node.node_type
        ));
        for dep in &node.depends_on {
            dot.push_str(&format!("    {} -> {};\n", node.id, dep));
        }
    }
    dot.push_str("}\n");
    fs::write(&output, dot)?;
    println!("✅ Graph written to {}", output.display());
    Ok(())
}

/// Analyze a DSL YAML architecture for cycles and bottlenecks
pub fn analyze(file: PathBuf, json: bool, bottleneck: usize) -> Result<()> {
    let mut dsl = ferrum_compiler::parse_dsl_yaml(&file)?;
    let modules = ferrum_compiler::project_to_modules(&mut dsl);
    let graph = ferrum_compiler::build_graph(&modules);
    let layers = ferrum_compiler::classify_layers(&modules);
    let cycles = ferrum_compiler::find_cycles(&graph);
    let bottlenecks = ferrum_compiler::find_bottlenecks(&graph, bottleneck);
    if json {
        let out = serde_json::json!({
            "cycles": cycles,
            "bottlenecks": bottlenecks,
            "layers": layers,
        });
        println!("{}", serde_json::to_string_pretty(&out)?);
    } else {
        if cycles.is_empty() {
            println!("✅ No dependency cycles detected");
        } else {
            println!("⚠️ Found {} cycle(s):", cycles.len());
            for c in cycles {
                println!("  - {}", c.join(" -> "));
            }
        }
        if bottlenecks.is_empty() {
            println!("✅ No bottlenecks detected");
        } else {
            println!("⚠️ Potential bottlenecks: {}", bottlenecks.join(", "));
        }
        println!("Layers:");
        for (layer, nodes) in layers {
            println!("  - {:?}: {} node(s)", layer, nodes.len());
        }
    }
    Ok(())
}

/// Fill AI markers like `⛳️ AI_FILL[...]` by calling the AI service.
pub fn fill_todos(dir: PathBuf) -> Result<()> {
    use regex::Regex;
    use reqwest::blocking::Client;
    use serde_json::json;
    use std::fs;
    use walkdir::WalkDir;

    let re =
        Regex::new(r"// \xE2\x9B\xB3 AI_FILL\[(?P<task>[^\]]+)\] --context=(?P<context>[^\n]+)")
            .unwrap();
    let client = Client::new();

    for entry in WalkDir::new(&dir).into_iter().filter_map(Result::ok) {
        let path = entry.path();
        if path.is_file() {
            if let Ok(contents) = fs::read_to_string(path) {
                if contents.contains("AI_FILL") {
                    let replaced = re.replace_all(&contents, |caps: &regex::Captures| {
                        let resp = client
                            .post("http://localhost:8000/fill-todo")
                            .json(&json!({
                                "task": &caps["task"],
                                "context": &caps["context"],
                            }))
                            .send()
                            .and_then(|r| r.json::<serde_json::Value>())
                            .ok();
                        let code_str = resp
                            .as_ref()
                            .and_then(|v| v.get("code"))
                            .and_then(|v| v.as_str())
                            .unwrap_or("// failed to fill");
                        code_str.to_string()
                    });
                    fs::write(path, replaced.as_bytes())?;
                    println!("Filled markers in {}", path.display());
                }
            }
        }
    }
    Ok(())
}

/// Send a prompt to the coordinator AI team.
pub fn ai_team(text: String) -> Result<()> {
    use crate::config::LlmConfig;
    use reqwest::blocking::Client;
    use std::io::{self, Read};
    use atty::Stream;

    let cfg_model = LlmConfig::load().and_then(|c| c.model);
    let model = std::env::var("MODEL")
        .ok()
        .or(cfg_model)
        .unwrap_or_else(|| "openai".to_string());

    let mut prompt = text;
    if !atty::is(Stream::Stdin) {
        let mut buf = String::new();
        io::stdin().read_to_string(&mut buf)?;
        if !buf.trim().is_empty() {
            prompt.push_str("\n");
            prompt.push_str(&buf);
        }
    }

    let client = Client::new();
    let resp = client
        .post("http://localhost:8000/ai-team")
        .json(&serde_json::json!({
            "messages": [{"role": "user", "content": prompt}],
            "model": model,
        }))
        .send()?;

    let value = resp.json::<serde_json::Value>()?;
    let reply = value
        .get("message")
        .and_then(|v| v.as_str())
        .unwrap_or("");

    println!("{}", reply);
    Ok(())
}

/// Generate an execution flow report for a DSL YAML file using the AI service.
pub fn flow_report(file: PathBuf) -> Result<()> {
    use reqwest::blocking::Client;
    use std::fs;

    let yaml = fs::read_to_string(&file)?;
    let client = Client::new();
    let resp = client
        .post("http://localhost:8000/simulate/flow")
        .json(&serde_json::json!({ "yaml": yaml }))
        .send()?;

    let value: serde_json::Value = resp.json()?;
    let text = value
        .get("text")
        .and_then(|v| v.as_str())
        .unwrap_or("");

    println!("{}", text);
    Ok(())
}

/// Build the backend using Cargo with optional target triple.
pub fn build(target: Option<String>) -> Result<()> {
    use std::process::Command;

    let mut cmd = Command::new("cargo");
    cmd.arg("build")
        .arg("--manifest-path")
        .arg("backend/Cargo.toml");
    if let Some(t) = target {
        cmd.arg("--target").arg(t);
    }
    let status = cmd.status()?;
    if !status.success() {
        anyhow::bail!("Cargo build failed");
    }
    println!("✅ Build finished");
    Ok(())
}

fn load_plugins() -> Result<ferrum_engine::PluginManager> {
    use std::fs;
    use std::path::PathBuf;
    let mut manager = ferrum_engine::PluginManager::new();
    let file_path = PathBuf::from(".ferrum/plugins.txt");
    if file_path.exists() {
        let contents = fs::read_to_string(file_path)?;
        for name in contents.lines() {
            let entry = name.trim();
            match entry {
                "graphql" => manager.register(ferrum_engine::plugins::GraphQLPlugin),
                "auth" => manager.register(ferrum_engine::plugins::AuthPlugin),
                "auth-password" => manager.register(ferrum_engine::plugins::AuthPasswordPlugin),
                "auth-oauth" => manager.register(ferrum_engine::plugins::AuthOAuthPlugin),
                "stripe" => manager.register(ferrum_engine::plugins::StripePlugin),
                "cron" => manager.register(ferrum_engine::plugins::CronPlugin),
                "cms-sanity" => manager.register(ferrum_engine::plugins::CmsSanityPlugin),
                "cms-notion" => manager.register(ferrum_engine::plugins::CmsNotionPlugin),
                "realtime-sse" => manager.register(ferrum_engine::plugins::RealtimeSsePlugin),
                other => {
                    let path = PathBuf::from(other);
                    if path.exists() {
                        let meta_path = path.join("plugin.toml");
                        if meta_path.exists() {
                            if let Ok(meta) =
                                ferrum_engine::plugins::PluginMetadata::from_file(&meta_path)
                            {
                                let lib_path = path.join(&meta.library);
                                unsafe {
                                    if let Ok(p) =
                                        ferrum_engine::plugins::DynamicPlugin::load(&lib_path)
                                    {
                                        manager.register(p);
                                        continue;
                                    }
                                }
                            }
                        }
                        println!("⚠️ Could not load plugin at {}", other);
                    } else if !other.is_empty() {
                        println!("⚠️ Unknown plugin '{}'", other);
                    }
                }
            }
        }
    }
    Ok(manager)
}
