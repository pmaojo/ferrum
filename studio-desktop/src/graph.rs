use crate::api;
use bevy::prelude::*;
use serde::{Deserialize, Serialize};
use std::collections::HashMap;
use std::sync::{mpsc::Receiver, Arc, Mutex};

use crate::layout::LayoutEngine;
use crate::runtime::AsyncRuntime;

#[derive(Debug, Deserialize, Serialize, Clone)]
pub struct Node {
    pub name: String,
    #[serde(default)]
    pub node_type: Option<String>,
    #[serde(default)]
    pub description: Option<String>,
    #[serde(default)]
    pub story: Option<String>,
    #[serde(default)]
    pub calls: Option<Vec<String>>,
    #[serde(default)]
    pub used_by: Option<Vec<String>>,
}

#[derive(Resource, Default, Clone)]
pub struct GraphData {
    pub nodes: Vec<Node>,
}

#[derive(Resource, Default)]
pub struct NodePositions(pub HashMap<String, Vec2>);

#[derive(Resource, Default)]
pub struct GraphTask(pub Option<(Arc<Mutex<Receiver<reqwest::Result<String>>>>,)>);

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

pub fn spawn_graph_request(
    rt: &AsyncRuntime,
    question: String,
) -> Arc<Mutex<Receiver<reqwest::Result<String>>>> {
    let (tx, rx) = std::sync::mpsc::channel();
    let rt = rt.0.clone();
    std::thread::spawn(move || {
        let res = rt.block_on(api::fetch_graph(&question));
        let _ = tx.send(res);
    });
    Arc::new(Mutex::new(rx))
}

pub fn load_graph(
    rt: Res<AsyncRuntime>,
    mut task: ResMut<GraphTask>,
    mut state: ResMut<crate::ui::UiState>,
    data: Res<GraphData>,
    mut pos: ResMut<NodePositions>,
) {
    let rx = spawn_graph_request(&rt, state.query.clone());
    task.0 = Some((rx,));
    state.loading = true;

    if !data.nodes.is_empty() {
        let names: Vec<String> = data.nodes.iter().map(|n| n.name.clone()).collect();
        pos.0 = LayoutEngine::circular_layout(&names, 200.0);
    }
}

pub fn update_graph_task(
    mut data: ResMut<GraphData>,
    mut pos: ResMut<NodePositions>,
    mut task: ResMut<GraphTask>,
    mut state: ResMut<crate::ui::UiState>,
) {
    let maybe_res = task
        .0
        .as_ref()
        .and_then(|rx| rx.0.lock().unwrap().try_recv().ok());

    if let Some(res) = maybe_res {
        state.loading = false;
        task.0 = None;
        if let Ok(g) = res {
            if let Ok(nodes) = serde_yaml::from_str::<Vec<Node>>(&g) {
                let names: Vec<String> = nodes.iter().map(|n| n.name.clone()).collect();
                pos.0 = LayoutEngine::circular_layout(&names, 200.0);
                data.nodes = nodes;
            }
        }
    }
}
