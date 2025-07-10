//! Placeholder graph viewer components.
//!
//! This module will eventually render an interactive graph using
//! [D3.js](https://d3js.org/) or a pure Rust/WebAssembly solution.
//! The goal is to replicate the UX from the desktop viewer.

use leptos::*;
use crate::{api::GraphApi, graph::GraphData};
use wasm_bindgen_futures::spawn_local;
use ferrum_shared_models::Node;
use std::{collections::HashMap, sync::Arc};

/// 2D point used when positioning nodes.
#[derive(Debug, Clone, Copy, PartialEq)]
pub struct Position {
    /// Horizontal coordinate in pixels.
    pub x: f32,
    /// Vertical coordinate in pixels.
    pub y: f32,
}

/// Compute edges from [`GraphData`].
///
/// An edge represents a `depends_on` relationship between two nodes and is
/// returned as a tuple `(source, target)` with node identifiers.
pub fn edges(data: &GraphData) -> Vec<(String, String)> {
    let ids: std::collections::HashSet<_> =
        data.nodes.iter().map(|n| n.id.clone()).collect();
    let mut result = Vec::new();
    for node in &data.nodes {
        for dep in &node.depends_on {
            if ids.contains(dep) {
                result.push((node.id.clone(), dep.clone()));
            }
        }
    }
    result
}

/// Generate a naive grid layout for the given [`GraphData`].
///
/// Returned positions are keyed by node identifier.
pub fn layout(data: &GraphData) -> HashMap<String, Position> {
    let mut map = HashMap::new();
    if data.nodes.is_empty() {
        return map;
    }

    let cols = (data.nodes.len() as f32).sqrt().ceil() as usize;
    for (idx, node) in data.nodes.iter().enumerate() {
        let col = idx % cols;
        let row = idx / cols;
        map.insert(
            node.id.clone(),
            Position {
                x: (col as f32) * 120.0 + 60.0,
                y: (row as f32) * 120.0 + 60.0,
            },
        );
    }
    map
}

/// Run simulation for a single node via [`GraphApi`].
pub async fn simulate(api: Arc<dyn GraphApi>, yaml: String) {
    let _ = api.simulate_flow(&yaml).await;
}

/// Store node metadata using [`GraphApi`].
pub async fn store_info(api: Arc<dyn GraphApi>, node: Node) {
    let _ = api
        .store_node_info(
            &node.id,
            node.description.as_deref(),
            node.story.as_deref(),
        )
        .await;
}

/// Renders the provided [`GraphData`] as SVG elements.
#[component]
pub fn GraphViewer(data: GraphData, api: Arc<dyn GraphApi>) -> impl IntoView {
    let positions = layout(&data);
    let lines = edges(&data);

    view! {
        <svg width="800" height="600">
            {lines
                .iter()
                .filter_map(|(s, t)| {
                    positions.get(s).zip(positions.get(t)).map(|(a, b)| {
                        view! {
                            <line x1={a.x} y1={a.y} x2={b.x} y2={b.y} stroke="gray"/>
                        }
                    })
                })
                .collect_view()}

            {data
                .nodes
                .iter()
                .map(|node| {
                    let pos = positions.get(&node.id).copied().unwrap_or(Position { x: 0.0, y: 0.0 });
                    let yaml = serde_yaml::to_string(node).unwrap_or_default();
                    let on_sim = {
                        let api = api.clone();
                        let yaml = yaml.clone();
                        move |_| spawn_local(simulate(api.clone(), yaml.clone()))
                    };
                    let on_store = {
                        let api = api.clone();
                        let n = node.clone();
                        move |_| spawn_local(store_info(api.clone(), n.clone()))
                    };

                    view! {
                        <g transform={format!("translate({},{})", pos.x, pos.y)}>
                            <circle r="20" fill="lightblue" stroke="black" on:click=on_sim />
                            <text y="4" text-anchor="middle">{node.id.clone()}</text>
                            <text y="30" on:click=on_store class="action">"save"</text>
                        </g>
                    }
                })
                .collect_view()}
        </svg>
    }
}

