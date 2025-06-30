use anyhow::Result;
use clap::Parser;
use ferrum_cli::commands::{compile, dev, init, migrate, prompt, sync, add_plugin, list_plugins, Cli, Commands};

fn main() -> Result<()> {
    // Initialize logging
    tracing_subscriber::fmt()
        .with_max_level(tracing::Level::INFO)
        .with_target(false)
        .init();

    let cli = Cli::parse();

    match cli.command {
        Commands::Compile {
            file,
            output,
            templates,
        } => compile(file, output, templates),
        Commands::Prompt { text, output } => prompt(text, output),
        Commands::Dev {
            with_graph,
            with_ai,
        } => dev(with_graph, with_ai),
        Commands::Init {
            name,
            with_graph,
            with_ai,
            with_db,
            with_auth,
            with_jobs,
            with_uploads,
        } => init(name, with_graph, with_ai, with_db, with_auth, with_jobs, with_uploads),
        Commands::Sync {
            file,
            uri,
            user,
            password,
        } => sync(file, uri, user, password),
        Commands::Migrate {} => migrate(),
        Commands::Add { plugin } => add_plugin(plugin),
        Commands::List {} => list_plugins(),
    }
}
