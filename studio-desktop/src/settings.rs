use bevy::prelude::*;

/// User-provided location of the `grafo.yaml` file.
#[derive(Resource, Clone)]
pub struct ProjectSettings {
    /// Path to the `grafo.yaml` file used for compilation.
    pub grafo_path: String,
    /// Whether the user has confirmed the path.
    pub confirmed: bool,
}

impl Default for ProjectSettings {
    fn default() -> Self {
        Self { grafo_path: "grafo.yaml".into(), confirmed: false }
    }
}
