use crate::api;
use bevy::prelude::*;
use bevy_tokio_tasks::tokio::task::JoinHandle;
pub use ferrum_shared_models::Node;
use std::collections::HashMap;


use crate::layout::LayoutEngine;
use bevy_tokio_tasks::TokioTasksRuntime;
use crate::app_state::AppState;
use bevy::prelude::NextState;


#[derive(Resource, Default, Clone)]
pub struct GraphData {
    pub nodes: Vec<Node>,
}

#[derive(Resource, Default)]
pub struct NodePositions(pub HashMap<String, Vec2>);

#[derive(Resource, Default)]
pub struct GraphTask(pub Option<bevy_tokio_tasks::tokio::task::JoinHandle<reqwest::Result<String>>>);

#[derive(Resource, Clone)]
pub struct Viewport {
    pub zoom: f32,
    pub offset: Vec2,
}

impl Default for Viewport {
    fn default() -> Self {
        Self {
            zoom: 1.0,
            offset: Vec2::ZERO,
        }
    }
}

pub fn spawn_graph_request(rt: &TokioTasksRuntime, question: String) -> JoinHandle<reqwest::Result<String>> {
    rt.spawn_background_task(move |_| async move { api::fetch_graph(&question).await })
}

pub fn load_graph(
    rt: Res<TokioTasksRuntime>,
    mut task: ResMut<GraphTask>,
    mut state: ResMut<crate::ui::UiState>,
    data: Res<GraphData>,
    mut pos: ResMut<NodePositions>,
    _writer: EventWriter<crate::api::LogEvent>,
) {
    let handle = spawn_graph_request(&rt, state.query.clone());
    task.0 = Some(handle);
    state.loading = true;

    if !data.nodes.is_empty() {
        let names: Vec<String> = data.nodes.iter().map(|n| n.id.clone()).collect();
        pos.0 = LayoutEngine::circular_layout(&names, 200.0);
    }
}

pub fn update_graph_task(
    mut data: ResMut<GraphData>,
    mut pos: ResMut<NodePositions>,
    mut task: ResMut<GraphTask>,
    mut state: ResMut<crate::ui::UiState>,
    mut next_state: ResMut<NextState<AppState>>,
    mut log_writer: EventWriter<crate::api::LogEvent>,
) {
    let maybe_res = if let Some(handle) = task.0.as_mut() {
        futures_lite::future::block_on(futures_lite::future::poll_once(handle))
    } else {
        None
    };

    if let Some(res) = maybe_res {
        state.loading = false;
        task.0 = None;
        match res {
            Ok(Ok(graph_yaml)) => {
                if let Ok(nodes) = serde_yaml::from_str::<Vec<Node>>(&graph_yaml) {
                    let names: Vec<String> = nodes.iter().map(|n| n.id.clone()).collect();
                    pos.0 = LayoutEngine::circular_layout(&names, 200.0);
                    data.nodes = nodes;
                    next_state.set(AppState::InGame);
                }
            }
            Ok(Err(err)) => {
                api::push_log(&mut log_writer, format!("Graph request error: {err}"));
                data.nodes.clear();
                next_state.set(AppState::InGame);
            }
            Err(err) => {
                api::push_log(&mut log_writer, format!("Graph task error: {err}"));
                data.nodes.clear();
                next_state.set(AppState::InGame);
            }
        }
    }
}
