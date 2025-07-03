use bevy::prelude::*;
use bevy_tokio_tasks::{TokioTasksPlugin, TokioTasksRuntime};

/// Type alias for the async runtime used by the application.
pub type AsyncRuntime = TokioTasksRuntime;

/// Returns the plugin that initializes the Tokio runtime.
pub fn runtime_plugin() -> impl Plugin {
    TokioTasksPlugin::default()
}
