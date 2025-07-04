use bevy::prelude::*;
use studio_desktop::app_state::AppState;
use studio_desktop::graph::{GraphData, GraphTask, NodePositions, Viewport};
use studio_desktop::ui::{viewer, BoxedFactory, UiState, AiTask, NodeInfoTask, LogBuffer, SvgImage};
use studio_desktop::api::LogEvent;
use bevy_egui::EguiContexts;

#[test]
fn draw_graph_skips_when_icons_missing() {
    let mut app = App::new();
    app.add_plugins(MinimalPlugins)
        .add_event::<LogEvent>()
        .init_state::<AppState>()
        .init_resource::<GraphData>()
        .init_resource::<NodePositions>()
        .init_resource::<Viewport>()
        .init_resource::<GraphTask>()
        .insert_resource(UiState::default())
        .insert_resource(BoxedFactory::default())
        .insert_resource(AiTask::default())
        .insert_resource(NodeInfoTask::default())
        .insert_resource(LogBuffer::default())
        .init_asset::<SvgImage>()
        .insert_resource(EguiContexts::default())
        .add_systems(
            Update,
            viewer::draw_graph
                .run_if(in_state(AppState::InGame))
                .run_if(resource_exists::<studio_desktop::ui::Icons>()),
        );

    app.world_mut().resource_mut::<State<AppState>>().set(AppState::InGame);

    app.update();
}
