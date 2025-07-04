use bevy::prelude::*;
use bevy_tokio_tasks::TokioTasksPlugin;

/// Returns the plugin that initializes the Tokio runtime.
pub fn runtime_plugin() -> impl Plugin {
    TokioTasksPlugin::default()
}
