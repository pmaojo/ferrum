use bevy::prelude::*;
use studio_desktop::api::LogEvent;
use studio_desktop::graph::{GraphData, NodePositions};
use studio_desktop::ui::viewer::{ViewerPlugin, TourState};
use studio_desktop::app_state::AppState;

#[test]
#[ignore]
fn viewer_plugin_registers_resources() {
    let mut app = App::new();
    app.add_plugins(DefaultPlugins)
        .add_plugins(bevy_egui::EguiPlugin::default())
        .add_plugins(bevy::state::app::StatesPlugin)
        .init_state::<AppState>()
        .add_plugins(ViewerPlugin);

    assert!(app.world().contains_resource::<GraphData>());
    assert!(app.world().contains_resource::<NodePositions>());
    assert!(app.world().contains_resource::<TourState>());
    app.world().resource::<Events<LogEvent>>();
}
