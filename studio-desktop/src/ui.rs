use crate::api;
use crate::graph::{GraphData, GraphTask, Node, NodePositions};
use crate::runtime::AsyncRuntime;
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
    pub loading: bool,
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
            loading: false,
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

#[derive(Resource, Default)]
pub struct AiTask(pub Option<std::sync::mpsc::Receiver<reqwest::Result<String>>>);

pub struct NodeUpdate {
    pub name: String,
    pub description: Option<String>,
    pub story: Option<String>,
    pub calls: Option<Vec<String>>,
    pub used_by: Option<Vec<String>>,
}

#[derive(Resource, Default)]
pub struct NodeInfoTask(pub Option<(NodeUpdate, std::sync::mpsc::Receiver<reqwest::Result<()>>)>);

pub fn graph_viewer(
    mut contexts: EguiContexts,
    mut data: ResMut<GraphData>,
    mut state: ResMut<UiState>,
    mut viewport: ResMut<crate::graph::Viewport>,
    mut positions: ResMut<NodePositions>,
    runtime: Res<AsyncRuntime>,
    mut graph_task: ResMut<GraphTask>,
    mut ai_task: ResMut<AiTask>,
    mut node_task: ResMut<NodeInfoTask>,
) {
    let ctx = contexts.ctx_mut();
    if let Some(rx) = &ai_task.0 {
        if let Ok(res) = rx.try_recv() {
            ai_task.0 = None;
            if let Ok(text) = res {
                state.ai_reply = Some(text);
            }
        }
    }
    if let Some(pending) = &mut node_task.0 {
        if let Ok(res) = pending.1.try_recv() {
            if res.is_ok() {
                if let Some(node) = data.nodes.iter_mut().find(|n| n.name == pending.0.name) {
                    node.description = pending.0.description.clone();
                    node.story = pending.0.story.clone();
                    node.calls = pending.0.calls.clone();
                    node.used_by = pending.0.used_by.clone();
                }
            }
            node_task.0 = None;
        }
    }
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
            if resp.secondary_clicked() {
                state.edit = Some(EditData {
                    name: node.name.clone(),
                    description: node.description.clone().unwrap_or_default(),
                    story: node.story.clone().unwrap_or_default(),
                    calls: node.calls.clone().unwrap_or_default().join(", "),
                    used_by: node.used_by.clone().unwrap_or_default().join(", "),
                });
            }
        }
    });
    egui::SidePanel::right("side_panel").show(ctx, |ui| {
        ui.heading("Graph Controls");
        ui.label("Question");
        ui.text_edit_singleline(&mut state.query);
        if ui.button("Regenerate").clicked() {
            let rx = crate::graph::spawn_graph_request(&runtime, state.query.clone());
            graph_task.0 = Some(rx);
            state.selected = None;
            state.loading = true;
        }
        if state.loading {
            ui.add(egui::Spinner::new());
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
                    let question = format!("What affects {}?", name);
                    let (tx, rx) = std::sync::mpsc::channel();
                    let rt = runtime.0.clone();
                    std::thread::spawn(move || {
                        let res = rt.block_on(api::ask_ai_team(&question));
                        let _ = tx.send(res);
                    });
                    ai_task.0 = Some(rx);
                }
                if let Some(reply) = &state.ai_reply {
                    ui.separator();
                    ui.label(reply);
                }
            }
        }
    });
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
                    if let Some(node) = data.nodes.iter().find(|n| n.name == edit.name) {
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
                        let update = NodeUpdate {
                            name: node.name.clone(),
                            description: desc.clone(),
                            story: story.clone(),
                            calls: if edit.calls.trim().is_empty() {
                                None
                            } else {
                                Some(
                                    edit.calls
                                        .split(',')
                                        .map(|s| s.trim().to_string())
                                        .collect(),
                                )
                            },
                            used_by: if edit.used_by.trim().is_empty() {
                                None
                            } else {
                                Some(
                                    edit.used_by
                                        .split(',')
                                        .map(|s| s.trim().to_string())
                                        .collect(),
                                )
                            },
                        };
                        let (tx, rx) = std::sync::mpsc::channel();
                        let rt = runtime.0.clone();
                        let name = update.name.clone();
                        let desc_clone = update.description.clone();
                        let story_clone = update.story.clone();
                        std::thread::spawn(move || {
                            let _ = rt.block_on(api::store_node_info(
                                &name,
                                desc_clone.as_deref(),
                                story_clone.as_deref(),
                            ));
                            let _ = tx.send(Ok(()));
                        });
                        node_task.0 = Some((update, rx));
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
