use bevy::prelude::*;
use crate::api;

#[derive(Resource, Default)]
pub struct GraphData(pub String);

pub fn load_graph(mut data: ResMut<GraphData>) {
    // Fetch graph on startup using a blocking request
    if let Ok(g) = api::fetch_graph_blocking("project overview") {
        data.0 = g;
    }
}
