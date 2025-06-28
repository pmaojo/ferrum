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

    /// Start development environment with Docker
    Dev {
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
}

/// Compile a `grafo.yaml` architecture file into source code.
pub fn compile(file: PathBuf, output: Option<PathBuf>, templates: Option<PathBuf>) -> Result<()> {
    let output_dir = output.unwrap_or_else(|| PathBuf::from("."));
    let templates_dir = templates.unwrap_or_else(|| PathBuf::from("templates"));

    let module = ferrum_compiler::parse_yaml(&file)?;
    ferrum_compiler::validate_module(&module)?;

    let generator = ferrum_compiler::Generator::new(templates_dir, output_dir)?;
    generator.generate(&module)?;

    println!("✅ Successfully compiled {}", file.display());
    Ok(())
}

/// Generate a `grafo.yaml` file from a free form prompt.
pub fn prompt(text: String, output: Option<PathBuf>) -> Result<()> {
    use reqwest::blocking::Client;
    use std::fs;

    println!("🤖 AI Architecture Generation");
    println!("━━━━━━━━━━━━━━━━━━━━━━━━━━━━");
    println!("Prompt: {}", text);
    println!();

    // Call Python AI service
    let client = Client::new();
    let response = client
        .post("http://localhost:8000/generate-yaml")
        .json(&serde_json::json!({ "text": text, "model": "gpt-4" }))
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

/// Start the local development environment using Docker.
pub fn dev(with_graph: bool, with_ai: bool) -> Result<()> {
    use std::process::Command;

    println!("🐳 Starting Ferrum development environment");
    println!("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━");

    // Create a docker-compose command with the appropriate services
    let mut services = vec!["backend", "frontend", "db"];

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
pub fn init(name: String, with_graph: bool, with_ai: bool, with_db: bool) -> Result<()> {
    use std::fs::{self, OpenOptions};
    use std::io::Write;

    println!("🏗️  Initializing new Ferrum project: {}", name);
    println!("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━");

    // Create project directory
    let project_dir = PathBuf::from(&name);
    fs::create_dir_all(&project_dir)?;

    // Create directory structure
    let dirs = [
        "backend/src",
        "frontend/src",
        "shared-models",
        "templates/backend",
        "templates/frontend",
        "templates/shared-models",
        "gen",
        "data/postgres",
    ];

    for dir in dirs.iter() {
        fs::create_dir_all(project_dir.join(dir))?;
        println!("📁 Created directory: {}/{}", name, dir);
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
        fs::create_dir_all(project_dir.join("backend/db/migrations"))?;
        fs::create_dir_all(project_dir.join("templates/backend/db/migrations"))?;
        println!("📁 Created directory: {}/backend/db/migrations", name);

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

        let mig_dir = project_dir.join("templates/backend/db/migrations/0001_create_users");
        fs::create_dir_all(&mig_dir)?;
        fs::write(
            mig_dir.join("up.sql"),
            include_str!("../../templates/backend/db/migrations/0001_create_users/up.sql"),
        )?;
        fs::write(
            mig_dir.join("down.sql"),
            include_str!("../../templates/backend/db/migrations/0001_create_users/down.sql"),
        )?;

        // Create .env with database URL
        fs::write(
            project_dir.join(".env"),
            "DATABASE_URL=postgres://ferrum:password@db/ferrum\n",
        )?;

        println!("📄 Added Diesel templates and .env file");
    }

    // Create docker-compose.yml
    let mut docker_compose = fs::File::create(project_dir.join("docker-compose.yml"))?;
    let mut docker_compose_content = include_str!("../../docker-compose.yml").to_string();
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
            "diesel = {{ version = \"2\", features = [\"postgres\"] }}"
        )?;
        writeln!(cargo_toml, "dotenvy = \"0.15\"")?;
        println!("📄 Updated backend/Cargo.toml with Diesel dependencies");
    }

    // Create README.md
    let mut readme = fs::File::create(project_dir.join("README.md"))?;
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
```

## Project Structure

- `backend/`: Rust backend using Axum
- `frontend/`: React frontend with TypeScript
- `shared-models/`: Shared models between backend and frontend
- `templates/`: Templates for code generation
- `gen/`: YAML architecture files
- `data/`: Persistent data for Docker services
"#,
        name
    );
    readme.write_all(readme_content.as_bytes())?;
    println!("📄 Created README.md");

    println!();
    println!("✅ Project initialized successfully!");
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
