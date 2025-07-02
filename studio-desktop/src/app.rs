use bevy::prelude::*;
use bevy_egui::{EguiPlugin, egui};

mod graph;
mod ui;
mod api;
mod layout;

pub fn run_app() {
    App::new()
        .add_plugins(DefaultPlugins)
        .add_plugins(EguiPlugin)
        .init_resource::<graph::GraphData>()
        .add_systems(Startup, graph::load_graph)
        .add_systems(Update, ui::graph_viewer)
        .run();
}
