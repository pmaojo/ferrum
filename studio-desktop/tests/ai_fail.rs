use bevy::prelude::*;
use bevy_tokio_tasks::TokioTasksRuntime;
use mockito::Server;
use studio_desktop::runtime::runtime_plugin;
use studio_desktop::ui::UiState;
use studio_desktop::ui::viewer::{AiTask, poll_ai_task};

#[test]
fn ai_task_failure_shows_popup() {
    // start mock server returning invalid data to trigger an error
    let mut server = Server::new_with_port(8001);
    let _m = server
        .mock("POST", "/ai-team")
        .with_status(500)
        .with_body("{}")
        .create();

    let mut app = App::new();
    app.add_plugins(MinimalPlugins)
        .add_plugins(runtime_plugin())
        .insert_resource(AiTask::default())
        .init_resource::<UiState>();

    // spawn failing task
    let question = "why".to_string();
    let rt = app.world().resource::<TokioTasksRuntime>().clone();
    let handle = rt.spawn_background_task(move |_| async move { studio_desktop::api::ask_ai_team(&question).await });
    app.world_mut().resource_mut::<AiTask>().0 = Some(handle);

    // poll until task completes
    for _ in 0..10 {
        app.world_mut().resource_scope(|world, mut task: Mut<AiTask>| {
            let mut state = world.resource_mut::<UiState>();
            poll_ai_task(&mut task, &mut state);
        });
        if app.world().resource::<AiTask>().0.is_none() {
            break;
        }
        std::thread::sleep(std::time::Duration::from_millis(10));
    }

    let state = app.world().resource::<UiState>();
    assert!(state.popup.as_deref().unwrap_or("").contains("error"));
}
