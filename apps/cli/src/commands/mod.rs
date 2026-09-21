use anyhow::Result;
use clap::{Parser, Subcommand, ValueEnum};
use std::path::PathBuf;

#[derive(Parser)]
#[command(name = "ferrum")]
#[command(about = "AI-first scaffolding system for full-stack applications", long_about = None)]
pub struct Cli {
    #[command(subcommand)]
    pub command: Commands,
}

#[derive(ValueEnum, Clone)]
pub enum DeployProvider {
    Fly,
    Railway,
    Render,
}

#[derive(ValueEnum, Clone)]
pub enum Frontend {
    React,
    Egui,
    LeptosCsr,
    LeptosSsr,
}

#[derive(ValueEnum, Clone)]
pub enum DbType {
    Postgres,
    Sqlite,
}

#[derive(Subcommand)]
pub enum Commands {
    /// Compile one or more YAML DSL files into code
    Compile {
        /// Path(s) or glob(s) to the DSL YAML files
        #[arg(value_name = "FILE", required = true, num_args=1..)]
        files: Vec<String>,

        /// Output directory for generated code
        #[arg(short, long, value_name = "DIR")]
        output: Option<PathBuf>,

        /// Templates directory
        #[arg(short, long, value_name = "DIR")]
        templates: Option<PathBuf>,

        /// Compile only this module
        #[arg(long, value_name = "NAME")]
        module: Option<String>,

        /// Treat the input YAML as a subgraph
        #[arg(long)]
        graph: bool,
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

        /// Choose database type
        #[arg(long, value_enum, default_value_t = DbType::Postgres)]
        db_type: DbType,

        /// Include authentication templates
        #[arg(long)]
        with_auth: bool,

        /// Include background job templates
        #[arg(long)]
        with_jobs: bool,

        /// Include file upload templates
        #[arg(long)]
        with_uploads: bool,

        /// Choose frontend framework
        #[arg(long, value_enum, default_value_t = Frontend::React)]
        frontend: Frontend,

        /// Skip starter templates
        #[arg(long)]
        nostarter: bool,

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

    /// Deploy the application to a provider
    Deploy {
        /// Deployment target provider
        #[arg(value_enum)]
        provider: DeployProvider,
    },
    /// Add a resource client (redis, s3, ...) to the DSL and generate it
    #[command(name = "make:resource")]
    MakeResource {
        /// Resource name, e.g. RedisCache
        name: String,
        /// Resource type, e.g. redis, s3
        #[arg(long)]
        resource_type: String,
        /// DSL file to add the resource to
        #[arg(long, default_value = "gen/example.yaml")]
        file: PathBuf,
    },
    /// Add a scheduled job to the DSL and generate it
    #[command(name = "make:job")]
    MakeJob {
        /// Job name, e.g. SendWeeklyDigest
        name: String,
        /// Cron schedule, e.g. "0 0 * * *"
        #[arg(long)]
        schedule: String,
        /// Handler identifier; defaults to the job name
        #[arg(long)]
        handler: Option<String>,
        /// DSL file to add the job to
        #[arg(long, default_value = "gen/example.yaml")]
        file: PathBuf,
    },
    /// Add an authorization policy to the DSL and generate it
    #[command(name = "make:policy")]
    MakePolicy {
        /// Policy name, e.g. AdminOnly
        name: String,
        /// Guard expression, e.g. "role:admin"
        #[arg(long)]
        guard: String,
        /// DSL file to add the policy to
        #[arg(long, default_value = "gen/example.yaml")]
        file: PathBuf,
    },
    /// Add a standalone entity to the DSL and generate its model, schema,
    /// migration and Diesel ORM files
    #[command(name = "make:entity")]
    MakeEntity {
        /// Entity name, e.g. Post
        name: String,
        /// Fields as name:type pairs, e.g. title:string body:text --field published:bool
        #[arg(long = "field", value_name = "NAME:TYPE")]
        fields: Vec<String>,
        /// Name of an existing entity to derive fields from
        #[arg(long)]
        derive_from: Option<String>,
        /// DSL file to add the entity to
        #[arg(long, default_value = "gen/example.yaml")]
        file: PathBuf,
        /// Template directory (defaults to the same one `ferrum compile` uses)
        #[arg(long)]
        templates: Option<PathBuf>,
    },
}

mod compile;
mod prompt;
mod component_prompt;
mod usecase_prompt;
mod generate_usecase;
mod dev;
mod init;
mod sync_cmd;
mod migrate;
mod doctor;
mod plugins;
mod explain;
mod plugin_docs;
mod extract_i18n;
mod generate_graph;
mod analyze;
mod fill_todos;
mod ai_team;
mod flow_report;
mod build;
mod deploy;
mod make;

pub use analyze::analyze;
pub use ai_team::ai_team;
pub use build::build;
pub use component_prompt::component_prompt;
pub use deploy::deploy;
pub use dev::dev;
pub use doctor::doctor;
pub use explain::explain;
pub use extract_i18n::extract_i18n;
pub use fill_todos::{fill_todos, fill_todos_with_pattern};
pub use flow_report::flow_report;
pub use generate_graph::generate_graph;
pub use generate_usecase::generate_usecase;
pub use init::init;
pub use migrate::migrate;
pub use plugin_docs::plugin_docs;
pub use prompt::prompt;
pub use sync_cmd::sync;
pub use usecase_prompt::usecase_prompt;
pub use compile::{compile, compile_with_formatters};
pub use plugins::{add_plugin, list_plugins, remove_plugin};
pub use make::{make_entity, make_job, make_policy, make_resource};

pub(crate) fn load_plugins() -> Result<ferrum_engine::plugins::PluginManager> {
    use std::fs;
    use std::path::PathBuf;
    let mut manager = ferrum_engine::plugins::PluginManager::new();
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
                            if let Ok(meta) = ferrum_engine::plugins::PluginMetadata::from_file(&meta_path) {
                                let lib_path = path.join(&meta.library);
                                if let Ok(p) = ferrum_engine::plugins::DynamicPlugin::load(&lib_path) {
                                    manager.register(p);
                                    continue;
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
