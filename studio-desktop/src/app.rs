use bevy::prelude::*;
use bevy_egui::{EguiPlugin, egui};

use crate::graph;
use crate::ui;
use crate::api;

pub fn run_app() {
    App::new()
        .add_plugins(DefaultPlugins)
        .add_plugins(EguiPlugin)
        .init_resource::<graph::GraphData>()
        .init_resource::<ui::UiState>()
        .add_systems(Startup, graph::load_graph)
        .add_systems(Update, ui::graph_viewer)
        .run();
}
