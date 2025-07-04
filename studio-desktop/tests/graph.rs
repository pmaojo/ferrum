use bevy::prelude::*;
use bevy_tokio_tasks::{TokioTasksPlugin, TokioTasksRuntime};
use bevy::state::app::StatesPlugin;
use studio_desktop::api::LogEvent;
use studio_desktop::graph::{self, GraphData, GraphTask, NodePositions};
use studio_desktop::ui::UiState;
use studio_desktop::app_state::AppState;

/// Spawn a failing graph request and poll the update task until it completes.
fn run_failed_request(app: &mut App) {
    // spawn an async request to a non-existent server to force an error
    let query = "test".to_string();
    let rt = app.world().resource::<TokioTasksRuntime>().clone();
    let handle = graph::spawn_graph_request(&rt, query);
    app.world_mut().resource_mut::<GraphTask>().0 = Some(handle);
    app.world_mut().resource_mut::<UiState>().loading = true;

    app.add_systems(Update, graph::update_graph_task);

    // repeatedly update until the task completes
    for _ in 0..10 {
        app.update();
        if app.world().resource::<GraphTask>().0.is_none() {
            break;
        }
        std::thread::sleep(std::time::Duration::from_millis(50));
    }
    // apply state transition
    app.update();
}

#[test]
fn failed_requests_emit_log() {
    let mut app = App::new();
    app.add_plugins(MinimalPlugins)
        .add_plugins(StatesPlugin)
        .add_plugins(TokioTasksPlugin::default())
        .init_state::<AppState>()
        .add_event::<LogEvent>()
        .init_resource::<GraphData>()
        .init_resource::<NodePositions>()
        .init_resource::<GraphTask>()
        .init_resource::<UiState>();

    run_failed_request(&mut app);

    let logs: Vec<String> = app
        .world_mut()
        .resource_mut::<Events<LogEvent>>()
        .drain()
        .map(|e| e.0)
        .collect();
    assert!(logs.iter().any(|l| l.contains("Graph request error") || l.contains("Graph task error")));
}

#[test]
fn failed_requests_transition_state() {
    let mut app = App::new();
    app.add_plugins(MinimalPlugins)
        .add_plugins(StatesPlugin)
        .add_plugins(TokioTasksPlugin::default())
        .init_state::<AppState>()
        .add_event::<LogEvent>()
        .init_resource::<GraphData>()
        .init_resource::<NodePositions>()
        .init_resource::<GraphTask>()
        .init_resource::<UiState>();

    run_failed_request(&mut app);

    let state = app.world().resource::<State<AppState>>();
    assert_eq!(*state.get(), AppState::InGame);
    assert!(app.world().resource::<GraphData>().nodes.is_empty());
}
