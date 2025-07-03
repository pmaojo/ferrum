use bevy::prelude::*;
use bevy_egui::{egui, EguiPlugin};

use crate::api;
use crate::graph;
use crate::runtime::AsyncRuntime;
use crate::ui;
use crate::ui::{AiTask, Icons, LogBuffer, NodeInfoTask};
use std::sync::{mpsc::Receiver, Arc, Mutex};

#[derive(Resource)]
struct LogReceiver(pub Arc<Mutex<Receiver<String>>>);

pub fn run_app(log_rx: Receiver<String>, runtime: AsyncRuntime) {
    App::new()
        .add_plugins(DefaultPlugins)
        .add_plugins(EguiPlugin)
        .init_resource::<graph::GraphData>()
        .init_resource::<graph::NodePositions>()
        .init_resource::<graph::Viewport>()
        .init_resource::<ui::UiState>()
        .init_resource::<ui::Icons>()
        .init_resource::<graph::GraphTask>()
        .insert_resource(AiTask::default())
        .insert_resource(NodeInfoTask::default())
        .insert_resource(LogBuffer::default())
        .insert_resource(LogReceiver(Arc::new(Mutex::new(log_rx))))
        .insert_resource(runtime)
        .add_systems(Update, collect_logs)
        .add_systems(Startup, graph::load_graph)
        .add_systems(
            Update,
            (graph::update_graph_task, ui::graph_viewer, ui::log_panel),
        )
        .run();
}

fn collect_logs(rx: Res<LogReceiver>, mut buf: ResMut<LogBuffer>) {
    let mut guard = rx.0.lock().unwrap();
    while let Ok(line) = guard.try_recv() {
        buf.0.push_back(line);
        if buf.0.len() > 200 {
            buf.0.pop_front();
        }
    }
}
