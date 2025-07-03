use bevy::prelude::*;
use bevy_egui::EguiPlugin;

use crate::graph;
use crate::ui;
use crate::ui::{AiTask, Icons, LogBuffer, NodeInfoTask};
use bevy_tokio_tasks::TokioTasksPlugin;
use bevy_tokio_tasks::TokioTasksRuntime as AsyncRuntime;
use std::sync::{mpsc::Receiver, Arc, Mutex};

#[derive(Resource)]
struct LogReceiver(pub Arc<Mutex<Receiver<String>>>);

pub fn run_app(log_rx: Receiver<String>) {
    App::new()
        .add_plugins(DefaultPlugins)
        .add_plugins(EguiPlugin)
        .add_plugins(TokioTasksPlugin::default())
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
        .add_event::<ui::viewer::NodeAction>()
        .add_systems(Update, collect_logs)
        .add_systems(Startup, graph::load_graph)
        .add_systems(
            Update,
            (
                graph::update_graph_task,
                ui::viewer::process_async_results,
                ui::viewer::handle_interaction,
                ui::viewer::render_nodes,
                ui::viewer::context_menu_actions,
                ui::viewer::update_side_panel,
                ui::log_panel,
            ),
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
