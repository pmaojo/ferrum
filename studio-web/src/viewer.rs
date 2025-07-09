//! Placeholder graph viewer components.
//!
//! This module will eventually render an interactive graph using
//! [D3.js](https://d3js.org/) or a pure Rust/WebAssembly solution.
//! The goal is to replicate the UX from the desktop viewer.

use leptos::*;
use crate::graph::GraphData;

/// Renders the provided [`GraphData`] as SVG elements.
#[component]
pub fn GraphViewer(data: GraphData) -> impl IntoView {
    // TODO: implement interactive layout and node actions
    view! { <pre>{format!("{:#?}", data.nodes)}</pre> }
}

