use crate::api;
use bevy::prelude::*;
use serde::Deserialize;
use std::collections::HashMap;
use std::sync::mpsc::Receiver;

use crate::runtime::AsyncRuntime;

#[derive(Debug, Deserialize, Clone)]
pub struct Node {
    pub name: String,
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
pub struct GraphTask(pub Option<Receiver<reqwest::Result<String>>>);

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
) -> Receiver<reqwest::Result<String>> {
    let (tx, rx) = std::sync::mpsc::channel();
    let rt = rt.0.clone();
    std::thread::spawn(move || {
        let res = rt.block_on(api::fetch_graph(&question));
        let _ = tx.send(res);
    });
    rx
}

pub fn load_graph(
    rt: Res<AsyncRuntime>,
    mut task: ResMut<GraphTask>,
    mut state: ResMut<crate::ui::UiState>,
) {
    let rx = spawn_graph_request(&rt, state.query.clone());
    task.0 = Some(rx);
    state.loading = true;
}

pub fn update_graph_task(
    mut data: ResMut<GraphData>,
    mut pos: ResMut<NodePositions>,
    mut task: ResMut<GraphTask>,
    mut state: ResMut<crate::ui::UiState>,
) {
    if let Some(rx) = &task.0 {
        if let Ok(res) = rx.try_recv() {
            state.loading = false;
            task.0 = None;
            if let Ok(g) = res {
                if let Ok(nodes) = serde_yaml::from_str::<Vec<Node>>(&g) {
                    pos.0.clear();
                    let n = nodes.len().max(1) as f32;
                    let radius = 200.0;
                    for (i, node) in nodes.iter().enumerate() {
                        let angle = i as f32 * std::f32::consts::TAU / n;
                        pos.0.insert(
                            node.name.clone(),
                            Vec2::new(angle.cos() * radius, angle.sin() * radius),
                        );
                    }
                    data.nodes = nodes;
                }
            }
        }
    }
}
