use anyhow::Result;
use clap::Parser;
use ferrum_cli::commands::{
    add_plugin, compile, component_prompt, explain, generate_graph, list_plugins, migrate,
    plugin_docs, prompt, remove_plugin, sync, usecase_prompt, Cli, Commands,
};
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
        Commands::Component { text, output } => component_prompt(text, output),
        Commands::Usecase { text, output } => usecase_prompt(text, output),
        Commands::GenerateUsecase { name, output } => {
            ferrum_cli::commands::generate_usecase(name, output)
        }
        Commands::Dev {
            docker,
            with_graph,
            with_ai,
        } => ferrum_cli::commands::dev(docker, with_graph, with_ai),
        Commands::Init {
            name,
            with_graph,
            with_ai,
            with_db,
            with_auth,
            with_jobs,
            with_uploads,
            api_only,
            interactive,
        } => ferrum_cli::commands::init(
            name,
            with_graph,
            with_ai,
            with_db,
            with_auth,
            with_jobs,
            with_uploads,
            api_only,
            interactive,
        ),
        Commands::Sync {
            file,
            uri,
            user,
            password,
        } => sync(file, uri, user, password),
        Commands::Migrate {} => migrate(),
        Commands::Doctor {} => ferrum_cli::commands::doctor(),
        Commands::Add { plugin } => add_plugin(plugin),
        Commands::Remove { plugin } => remove_plugin(plugin),
        Commands::List {} => list_plugins(),
        Commands::Explain { file } => explain(file),
        Commands::Docs { plugin } => plugin_docs(plugin),
        Commands::I18n { dir, output } => ferrum_cli::commands::extract_i18n(dir, output),
        Commands::Graph { file, output } => generate_graph(file, output),
    }
}
