use crate::ui::{Icons, SvgImage, SvgImageLoader};
use bevy::prelude::*;
use bevy_asset_loader::prelude::*;
use bevy_egui::EguiPlugin;

use crate::api::LogEvent;
use crate::app_state::AppState;
use crate::ui::viewer::ViewerPlugin;
use std::sync::{mpsc::Receiver, Arc, Mutex};

#[derive(Resource)]
struct LogReceiver(pub Arc<Mutex<Receiver<String>>>);

pub fn run_app(log_rx: Receiver<String>) {
    App::new()
        .add_plugins(DefaultPlugins)
        .init_state::<AppState>()
        .init_asset::<SvgImage>()
        .init_asset_loader::<SvgImageLoader>()
        .add_loading_state(
            LoadingState::new(AppState::Loading)
                .continue_to_state(AppState::InGame)
                .load_collection::<Icons>(),
        )
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
