pub mod commands;
pub mod config;

// Re-export CLI types and functions
pub use commands::{
    add_plugin, analyze, ai_team, build, compile, compile_with_formatters,
    component_prompt, deploy, dev, doctor, explain, extract_i18n, fill_todos,
    fill_todos_with_pattern, flow_report, generate_graph, generate_usecase,
    init, list_plugins, make_job, make_policy, make_resource, migrate,
    plugin_docs, prompt, remove_plugin, sync, usecase_prompt, Cli, Commands,
};
