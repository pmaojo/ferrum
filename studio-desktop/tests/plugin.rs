use bevy::prelude::*;
use studio_desktop::api::LogEvent;
use studio_desktop::graph::{GraphData, NodePositions};
use studio_desktop::ui::viewer::ViewerPlugin;

#[test]
fn viewer_plugin_registers_resources() {
    let mut app = App::new();
    app.add_plugins(MinimalPlugins).add_plugins(ViewerPlugin);
    app.update();

    assert!(app.world.contains_resource::<GraphData>());
    assert!(app.world.contains_resource::<NodePositions>());
    app.world.resource::<Events<LogEvent>>();
}
