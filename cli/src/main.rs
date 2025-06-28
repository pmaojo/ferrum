use anyhow::Result;
use clap::Parser;
use ferrum_cli::commands::{Cli, Commands, compile, prompt};
use tracing_subscriber::fmt::format;

fn main() -> Result<()> {
    // Initialize logging
    tracing_subscriber::fmt()
        .with_env_filter("info")
        .with_target(false)
        .init();

    let cli = Cli::parse();

    match cli.command {
        Commands::Compile { file, output, templates } => {
            compile(file, output, templates)
        },
        Commands::Prompt { text, output } => {
            prompt(text, output)
        },
    }
}
