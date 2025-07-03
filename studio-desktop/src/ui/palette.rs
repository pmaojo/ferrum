use bevy::prelude::*;
use bevy_egui::{egui, EguiContexts};

use crate::graph::{GraphData, Node, NodePositions, Viewport};
use super::UiState;

#[derive(Clone, Debug, PartialEq)]
pub struct NodeTemplate {
    pub label: String,
    pub node_type: Option<String>,
}

#[derive(Resource, Clone)]
pub struct NodeTemplates(pub Vec<NodeTemplate>);

impl Default for NodeTemplates {
    fn default() -> Self {
        Self(vec![
            NodeTemplate {
                label: "component".into(),
                node_type: Some("component".into()),
            },
            NodeTemplate {
                label: "service".into(),
                node_type: Some("service".into()),
            },
        ])
    }
}

pub fn node_palette(
    mut contexts: EguiContexts,
    templates: Res<NodeTemplates>,
    mut state: ResMut<UiState>,
) {
    let ctx = contexts.ctx_mut();
    egui::SidePanel::left("node_palette").show(ctx, |ui| {
        ui.heading("Palette");
        for temp in templates.0.iter() {
            let resp = ui.label(&temp.label).sense(egui::Sense::drag());
            if resp.drag_started() {
                state.palette_dragging = Some(temp.clone());
            }
        }
    });
}

pub fn handle_drop(
    ctx: &egui::Context,
    rect: egui::Rect,
    viewport: &Viewport,
    state: &mut UiState,
    data: &mut GraphData,
    positions: &mut NodePositions,
) {
    if let Some(template) = state.palette_dragging.clone() {
        if ctx.input(|i| i.pointer.any_released()) {
            if let Some(pos) = ctx.input(|i| i.pointer.interact_pos()) {
                if rect.contains(pos) {
                    let center = rect.center().to_vec2() + super::viewer::to_egui(viewport.offset);
                    let graph_pos = (pos.to_vec2() - center) / viewport.zoom;
                    let name = format!("{}{}", template.label, data.nodes.len() + 1);
                    data.nodes.push(Node {
                        name: name.clone(),
                        node_type: template.node_type.clone(),
                        description: None,
                        story: None,
                        calls: None,
                        used_by: None,
                    });
                    positions.0.insert(name, graph_pos);
                }
            }
            state.palette_dragging = None;
        }
    }
}
