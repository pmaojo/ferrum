use anyhow::Result;
use clap::Parser;
use ferrum_cli::commands::{
    add_plugin, analyze, compile, component_prompt, dev, explain, fill_todos,
    generate_graph, init, list_plugins, migrate, plugin_docs, prompt, remove_plugin, sync,
    usecase_prompt, flow_report, Cli, Commands,
};

fn main() -> Result<()> {
    // Initialize logging
    tracing_subscriber::fmt()
        .with_max_level(tracing::Level::INFO)
        .with_target(false)
        .init();

    let cli = Cli::parse();

    match cli.command {
        Commands::Compile {
            files,
            output,
            templates,
            module,
            graph,
        } => compile(files, output, templates, module, graph),
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
        } => dev(docker, with_graph, with_ai),
        Commands::Init {
            name,
            with_graph,
            with_ai,
            with_db,
            with_auth,
            with_jobs,
            with_uploads,
            frontend,
            api_only,
            nostarter,
            interactive,
        } => init(
            name,
            with_graph,
            with_ai,
            with_db,
            with_auth,
            with_jobs,
            with_uploads,
            frontend,
            nostarter,
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
        Commands::FillTodos { dir } => fill_todos(dir, &cli.ai_url),
        Commands::Flow { file } => flow_report(file),
        Commands::Analyze { file, json, bottleneck } => {
            analyze(file, json, bottleneck)
        }
        Commands::AiTeam { text } => ferrum_cli::commands::ai_team(text),
        Commands::Build { target } => ferrum_cli::commands::build(target),
        Commands::Deploy { provider } => ferrum_cli::commands::deploy(provider),
    }
}
