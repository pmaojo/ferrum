use bevy::prelude::*;
use mockito::Server;
use studio_desktop::api::LogEvent;
use studio_desktop::app_state::AppState;
use studio_desktop::graph::{load_graph, update_graph_task, GraphData, GraphTask, NodePositions};
use studio_desktop::runtime::runtime_plugin;
use studio_desktop::ui::UiState;

#[test]
fn graph_failure_transitions_to_ingame_and_logs() {
    let mut server = Server::new_with_port(8001);
    let _m = server
        .mock("POST", "/graph-rag")
        .with_status(500)
        .with_body("{}")
        .create();

    let mut app = App::new();
    app.add_plugins(MinimalPlugins)
        .add_plugins(runtime_plugin())
        .add_event::<LogEvent>()
        .init_state::<AppState>()
        .init_resource::<GraphData>()
        .init_resource::<NodePositions>()
        .init_resource::<GraphTask>()
        .init_resource::<UiState>()
        .add_systems(OnEnter(AppState::Loading), load_graph)
        .add_systems(Update, update_graph_task);

    app.update();
    for _ in 0..5 {
        app.update();
    }

    let state = app.world().resource::<State<AppState>>().get().clone();
    assert_eq!(state, AppState::InGame);
    let logs: Vec<String> = app
        .world_mut()
        .resource_mut::<Events<LogEvent>>()
        .drain()
        .map(|e| e.0)
        .collect();
    assert!(!logs.is_empty());
}
