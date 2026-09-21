use anyhow::Result;
use clap::Parser;
use ferrum_cli::{
    add_plugin, analyze, compile, component_prompt, dev, explain, fill_todos,
    generate_graph, init, list_plugins, migrate, plugin_docs, prompt,
    remove_plugin, sync, usecase_prompt, flow_report, generate_usecase,
    doctor, extract_i18n, ai_team, build, deploy, make_entity, make_job,
    make_policy, make_resource, Cli, Commands,
};

fn main() -> Result<()> {
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
            generate_usecase(name, output)
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
            db_type,
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
            db_type,
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
        Commands::Doctor {} => doctor(),
        Commands::Add { plugin } => add_plugin(plugin),
        Commands::Remove { plugin } => remove_plugin(plugin),
        Commands::List {} => list_plugins(),
        Commands::Explain { file } => explain(file),
        Commands::Docs { plugin } => plugin_docs(plugin),
        Commands::I18n { dir, output } => extract_i18n(dir, output),
        Commands::Graph { file, output } => generate_graph(file, output),
        Commands::FillTodos { dir } => fill_todos(dir),
        Commands::Flow { file } => flow_report(file),
        Commands::Analyze { file, json, bottleneck } => {
            analyze(file, json, bottleneck)
        }
        Commands::AiTeam { text } => ai_team(text),
        Commands::Build { target } => build(target),
        Commands::Deploy { provider } => deploy(provider),
        Commands::MakeResource {
            name,
            resource_type,
            file,
        } => make_resource(name, resource_type, file),
        Commands::MakeJob {
            name,
            schedule,
            handler,
            file,
        } => make_job(name, schedule, handler, file),
        Commands::MakePolicy { name, guard, file } => make_policy(name, guard, file),
        Commands::MakeEntity {
            name,
            fields,
            derive_from,
            file,
            templates,
        } => make_entity(name, fields, derive_from, file, templates),
    }
}
