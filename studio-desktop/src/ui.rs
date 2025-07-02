use crate::api;
use crate::graph::GraphData;
use bevy::prelude::*;
use bevy_egui::{egui, EguiContexts};
use std::collections::HashMap;

#[derive(Resource, Default)]
pub struct UiState {
    pub selected: Option<String>,
    pub ai_reply: Option<String>,
}

pub fn graph_viewer(
    mut contexts: EguiContexts,
    data: Res<GraphData>,
    mut state: ResMut<UiState>,
    mut viewport: ResMut<crate::graph::Viewport>,
) {
    let ctx = contexts.ctx_mut();
    let (zoom_delta, pointer_delta, dragging) =
        ctx.input(|i| (i.zoom_delta(), i.pointer.delta(), i.pointer.primary_down()));
    if zoom_delta != 1.0 {
        viewport.zoom = (viewport.zoom * zoom_delta).clamp(0.2, 5.0);
    }
    if dragging {
        viewport.offset += pointer_delta;
    }

    egui::CentralPanel::default().show(ctx, |ui| {
        ui.heading("Graph View");
        let rect = ui.max_rect();
        let painter = ui.painter_at(rect);
        let n = data.nodes.len().max(1) as f32;
        let center = rect.center() + viewport.offset;
        let radius = rect.width().min(rect.height()) * 0.4 * viewport.zoom;
        let mut positions: HashMap<&str, egui::Pos2> = HashMap::new();
        for (i, node) in data.nodes.iter().enumerate() {
            let angle = i as f32 * std::f32::consts::TAU / n;
            let pos = center + egui::vec2(angle.cos(), angle.sin()) * radius;
            positions.insert(node.name.as_str(), pos);
        }
        // Draw edges
        for node in &data.nodes {
            if let Some(calls) = &node.calls {
                for target in calls {
                    if let (Some(&a), Some(&b)) = (
                        positions.get(node.name.as_str()),
                        positions.get(target.as_str()),
                    ) {
                        painter.line_segment(
                            [a, b],
                            egui::Stroke::new(1.0, egui::Color32::LIGHT_GRAY),
                        );
                    }
                }
            }
        }
        // Draw nodes
        for node in &data.nodes {
            let pos = positions[&node.name.as_str()];
            let rect = egui::Rect::from_center_size(pos, egui::vec2(40.0, 40.0));
            let resp = ui.allocate_rect(rect, egui::Sense::click());
            let color = if state.selected.as_deref() == Some(node.name.as_str()) {
                egui::Color32::LIGHT_BLUE
            } else {
                egui::Color32::from_rgb(100, 150, 250)
            };
            painter.circle_filled(pos, 20.0, color);
            painter.text(
                pos,
                egui::Align2::CENTER_CENTER,
                &node.name,
                egui::FontId::proportional(14.0),
                egui::Color32::BLACK,
            );
            if resp.hovered() {
                if let Some(desc) = &node.description {
                    egui::show_tooltip_at_pointer(
                        ui.ctx(),
                        egui::Id::new(format!("tip_{}", node.name)),
                        |ui| {
                            ui.label(desc);
                        },
                    );
                }
            }
            if resp.clicked() {
                state.selected = Some(node.name.clone());
                state.ai_reply = None;
            }
        }
        ui.separator();
        if let Some(name) = &state.selected {
            if let Some(node) = data.nodes.iter().find(|n| &n.name == name) {
                ui.label(format!("Selected: {}", name));
                if let Some(story) = &node.story {
                    egui::CollapsingHeader::new("Story").show(ui, |ui| {
                        ui.label(story);
                    });
                }
                if ui.button("Ask AI Team").clicked() {
                    if let Ok(reply) = api::ask_ai_team(&format!("What affects {}?", name)) {
                        state.ai_reply = Some(reply);
                    }
                }
                if let Some(reply) = &state.ai_reply {
                    ui.separator();
                    ui.label(reply);
                }
            }
        }
    });
}
