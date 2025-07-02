use crate::api;
use bevy::prelude::*;
use serde::Deserialize;
use std::collections::HashMap;

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

#[derive(Resource, Default, Clone)]
pub struct NodePositions(pub HashMap<String, Vec2>);

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

pub fn load_graph(mut data: ResMut<GraphData>, mut pos: ResMut<NodePositions>) {
    if let Ok(g) = api::fetch_graph_blocking("project overview") {
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
