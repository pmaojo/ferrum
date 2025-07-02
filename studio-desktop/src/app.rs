use bevy::prelude::*;
use bevy_egui::{egui, EguiPlugin};

use crate::api;
use crate::graph;
use crate::ui;
use crate::ui::LogBuffer;
use std::sync::mpsc::Receiver;

#[derive(Resource)]
struct LogReceiver(pub Receiver<String>);

pub fn run_app(log_rx: Receiver<String>) {
    App::new()
        .add_plugins(DefaultPlugins)
        .add_plugins(EguiPlugin)
        .init_resource::<graph::GraphData>()
        .init_resource::<graph::NodePositions>()
        .init_resource::<graph::Viewport>()
        .init_resource::<ui::UiState>()
        .insert_resource(LogBuffer::default())
        .insert_resource(LogReceiver(log_rx))
        .add_systems(Update, collect_logs)
        .add_systems(Startup, graph::load_graph)
        .add_systems(Update, (ui::graph_viewer, ui::log_panel))
        .run();
}

fn collect_logs(rx: Res<LogReceiver>, mut buf: ResMut<LogBuffer>) {
    while let Ok(line) = rx.try_recv() {
        buf.0.push_back(line);
        if buf.0.len() > 200 {
            buf.0.pop_front();
        }
    }
}
