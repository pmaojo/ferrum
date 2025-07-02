use bevy::prelude::*;
use serde::Deserialize;
use crate::api;

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

pub fn load_graph(mut data: ResMut<GraphData>) {
    if let Ok(g) = api::fetch_graph_blocking("project overview") {
        if let Ok(nodes) = serde_yaml::from_str::<Vec<Node>>(&g) {
            data.nodes = nodes;
        }
    }
}
