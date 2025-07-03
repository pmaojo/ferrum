use bevy::prelude::*;
use bevy_egui::EguiPlugin;

use crate::api::LogEvent;
use crate::graph;
use crate::ui;
use crate::ui::{AiTask, BuildTask, Icons, LogBuffer, NodeInfoTask};
use bevy_tokio_tasks::TokioTasksPlugin;
use bevy_tokio_tasks::TokioTasksRuntime as AsyncRuntime;
use std::sync::{Arc, Mutex, mpsc::Receiver};

#[derive(Resource)]
struct LogReceiver(pub Arc<Mutex<Receiver<String>>>);

pub fn run_app(log_rx: Receiver<String>) {
    App::new()
        .add_plugins(DefaultPlugins)
        .add_plugins(EguiPlugin)
        .add_plugins(TokioTasksPlugin::default())
        .add_event::<LogEvent>()
        .init_resource::<graph::GraphData>()
        .init_resource::<graph::NodePositions>()
        .init_resource::<graph::Viewport>()
        .init_resource::<ui::UiState>()
        .init_resource::<ui::Icons>()
        .init_resource::<graph::GraphTask>()
        .init_resource::<ui::BuildTask>()
        .insert_resource(AiTask::default())
        .insert_resource(NodeInfoTask::default())
        .insert_resource(LogBuffer::default())
        .insert_resource(LogReceiver(Arc::new(Mutex::new(log_rx))))
        .add_systems(Update, collect_logs)
        .add_systems(Startup, graph::load_graph)
        .add_systems(
            Update,
            (
                graph::update_graph_task,
                ui::viewer::handle_interaction,
                ui::viewer::draw_graph,
                ui::viewer::update_side_panel,
                ui::viewer::update_build_task,
                ui::log_panel,
            ),
        )
        .run();
}

fn collect_logs(rx: Res<LogReceiver>, mut writer: EventWriter<LogEvent>) {
    let Ok(mut guard) = rx.0.lock() else {
        eprintln!("failed to lock log receiver");
        return;
    };
    while let Ok(line) = guard.try_recv() {
        writer.send(LogEvent(line));
    }
}
