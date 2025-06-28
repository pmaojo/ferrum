use anyhow::Result;
use clap::Parser;
use ferrum_cli::commands::{compile, dev, init, prompt, Cli, Commands};

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
        } => init(name, with_graph, with_ai),
    }
}
