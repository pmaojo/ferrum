use bevy::prelude::*;
use bevy_egui::EguiPlugin;

use crate::api::LogEvent;
use crate::ui::viewer::ViewerPlugin;
use crate::app_state::AppState;
use std::sync::{Arc, Mutex, mpsc::Receiver};

#[derive(Resource)]
struct LogReceiver(pub Arc<Mutex<Receiver<String>>>);

pub fn run_app(log_rx: Receiver<String>) {
    App::new()
        .add_plugins(DefaultPlugins)
        .init_state::<AppState>()
        .add_plugins(EguiPlugin)
        .add_plugins(ViewerPlugin)
        .insert_resource(LogReceiver(Arc::new(Mutex::new(log_rx))))
        .add_systems(Update, collect_logs)
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
