use crate::api;
use crate::graph::{GraphData, Node, NodePositions};
use bevy::prelude::*;
use bevy_egui::{egui, EguiContexts};
use serde_yaml;
use std::collections::{HashMap, VecDeque};

#[derive(Resource)]
pub struct UiState {
    pub selected: Option<String>,
    pub ai_reply: Option<String>,
    pub dragging: Option<String>,
    pub edit: Option<EditData>,
    pub query: String,
    pub popup: Option<String>,
}

#[derive(Resource, Default)]
pub struct LogBuffer(pub VecDeque<String>);

impl Default for UiState {
    fn default() -> Self {
        Self {
            selected: None,
            ai_reply: None,
            dragging: None,
            edit: None,
            query: "project overview".to_string(),
            popup: None,
        }
    }
}

#[derive(Default)]
pub struct EditData {
    pub name: String,
    pub description: String,
    pub story: String,
    pub calls: String,
    pub used_by: String,
}

fn subgraph_yaml(data: &GraphData, name: &str) -> Option<String> {
    use std::collections::HashSet;
    let mut names = HashSet::new();
    let node = data.nodes.iter().find(|n| n.name == name)?;
    names.insert(name.to_string());
    if let Some(calls) = &node.calls {
        for c in calls {
            names.insert(c.clone());
        }
    }
    if let Some(used_by) = &node.used_by {
        for u in used_by {
            names.insert(u.clone());
        }
    }
    let nodes: Vec<Node> = data
        .nodes
        .iter()
        .filter(|n| names.contains(&n.name))
        .cloned()
        .collect();
    serde_yaml::to_string(&nodes).ok()
}

pub fn graph_viewer(
    mut contexts: EguiContexts,
    mut data: ResMut<GraphData>,
    mut state: ResMut<UiState>,
    mut viewport: ResMut<crate::graph::Viewport>,
    mut positions: ResMut<NodePositions>,
) {
    let ctx = contexts.ctx_mut();
    let (zoom_delta, pointer_delta, pointer_down) =
        ctx.input(|i| (i.zoom_delta(), i.pointer.delta(), i.pointer.primary_down()));
    if zoom_delta != 1.0 {
        viewport.zoom = (viewport.zoom * zoom_delta).clamp(0.2, 5.0);
    }
    if pointer_down {
        if let Some(name) = &state.dragging {
            if let Some(p) = positions.0.get_mut(name) {
                *p += pointer_delta / viewport.zoom;
            }
        } else {
            viewport.offset += pointer_delta;
        }
    } else {
        state.dragging = None;
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
            let pos = center + *positions.0.get(&node.name).unwrap_or(&Vec2::ZERO) * viewport.zoom;
            let rect = egui::Rect::from_center_size(pos, egui::vec2(40.0, 40.0));
            let resp = ui.allocate_rect(rect, egui::Sense::click_and_drag());
            if resp.drag_started() {
                state.dragging = Some(node.name.clone());
            }
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
            resp.context_menu(|ui| {
                if ui.button("Edit info").clicked() {
                    state.edit = Some(EditData {
                        name: node.name.clone(),
                        description: node.description.clone().unwrap_or_default(),
                        story: node.story.clone().unwrap_or_default(),
                        calls: node.calls.clone().unwrap_or_default().join(", "),
                        used_by: node.used_by.clone().unwrap_or_default().join(", "),
                    });
                }
                if ui.button("Simulate").clicked() {
                    if let Some(yaml) = subgraph_yaml(&data, &node.name) {
                        if let Ok(text) = api::simulate_flow(&yaml) {
                            state.popup = Some(text);
                        }
                    }
                }
                if ui.button("Generate").clicked() {
                    if let Ok(yaml) = api::generate_component(&node.name) {
                        state.popup = Some(yaml);
                    }
                }
                if ui.button("Validate").clicked() {
                    if let Some(yaml) = subgraph_yaml(&data, &node.name) {
                        if let Ok(ok) = api::validate_yaml(&yaml) {
                            state.popup = Some(if ok { "YAML válido".into() } else { "YAML inválido".into() });
                        }
                    }
                }
            });
        }
    });
    egui::SidePanel::right("side_panel").show(ctx, |ui| {
        ui.heading("Graph Controls");
        ui.label("Question");
        ui.text_edit_singleline(&mut state.query);
        if ui.button("Regenerate").clicked() {
            if let Ok(g) = api::fetch_graph_blocking(&state.query) {
                if let Ok(nodes) = serde_yaml::from_str::<Vec<Node>>(&g) {
                    positions.0.clear();
                    let n = nodes.len().max(1) as f32;
                    let radius = 200.0;
                    for (i, node) in nodes.iter().enumerate() {
                        let angle = i as f32 * std::f32::consts::TAU / n;
                        positions.0.insert(
                            node.name.clone(),
                            Vec2::new(angle.cos() * radius, angle.sin() * radius),
                        );
                    }
                    data.nodes = nodes;
                }
            }
            state.selected = None;
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
    if let Some(text) = &mut state.popup {
        egui::Window::new("Result").show(ctx, |ui| {
            ui.label(text);
            if ui.button("Close").clicked() {
                state.popup = None;
            }
        });
    }
    if let Some(edit) = &mut state.edit {
        egui::Window::new(format!("Edit {}", edit.name))
            .collapsible(false)
            .show(ctx, |ui| {
                ui.label("Description");
                ui.text_edit_singleline(&mut edit.description);
                ui.label("Story");
                ui.text_edit_multiline(&mut edit.story);
                ui.label("Calls (comma separated)");
                ui.text_edit_singleline(&mut edit.calls);
                ui.label("Used by (comma separated)");
                ui.text_edit_singleline(&mut edit.used_by);
                if ui.button("Save").clicked() {
                    if let Some(node) = data.nodes.iter_mut().find(|n| n.name == edit.name) {
                        let desc = if edit.description.trim().is_empty() {
                            None
                        } else {
                            Some(edit.description.clone())
                        };
                        let story = if edit.story.trim().is_empty() {
                            None
                        } else {
                            Some(edit.story.clone())
                        };
                        if api::store_node_info(&node.name, desc.as_deref(), story.as_deref())
                            .is_ok()
                        {
                            node.description = desc;
                            node.story = story;
                            node.calls = if edit.calls.trim().is_empty() {
                                None
                            } else {
                                Some(
                                    edit.calls
                                        .split(',')
                                        .map(|s| s.trim().to_string())
                                        .collect(),
                                )
                            };
                            node.used_by = if edit.used_by.trim().is_empty() {
                                None
                            } else {
                                Some(
                                    edit.used_by
                                        .split(',')
                                        .map(|s| s.trim().to_string())
                                        .collect(),
                                )
                            };
                        }
                    }
                    state.edit = None;
                }
                ui.same_line();
                if ui.button("Cancel").clicked() {
                    state.edit = None;
                }
            });
    }
}

pub fn log_panel(mut contexts: EguiContexts, logs: Res<LogBuffer>) {
    let ctx = contexts.ctx_mut();
    egui::TopBottomPanel::bottom("logs")
        .default_height(150.0)
        .show(ctx, |ui| {
            ui.heading("Logs");
            egui::ScrollArea::vertical().show(ui, |ui| {
                for line in logs.0.iter() {
                    ui.label(line);
                }
            });
        });
}
