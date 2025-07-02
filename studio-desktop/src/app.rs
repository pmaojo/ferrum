use bevy::prelude::*;
use bevy_egui::{egui, EguiPlugin};

use crate::api;
use crate::graph;
use crate::ui;

pub fn run_app() {
    App::new()
        .add_plugins(DefaultPlugins)
        .add_plugins(EguiPlugin)
        .init_resource::<graph::GraphData>()
        .init_resource::<graph::NodePositions>()
        .init_resource::<graph::Viewport>()
        .init_resource::<ui::UiState>()
        .add_systems(Startup, graph::load_graph)
        .add_systems(Update, ui::graph_viewer)
        .run();
}
