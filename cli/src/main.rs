use anyhow::Result;
use clap::Parser;
use ferrum_cli::commands::{compile, prompt, Cli, Commands};
use tracing::Level;

fn main() -> Result<()> {
    // Initialize logging
    tracing_subscriber::fmt()
        .with_max_level(Level::INFO)
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
        } => ferrum_cli::commands::dev(with_graph, with_ai),
        Commands::Init {
            name,
            with_graph,
            with_ai,
        } => ferrum_cli::commands::init(name, with_graph, with_ai),
    }
}
