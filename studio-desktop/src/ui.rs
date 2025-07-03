use crate::api;
use crate::graph::{GraphData, GraphTask, Node, NodePositions};
use crate::runtime::AsyncRuntime;
use bevy::prelude::*;
use bevy_egui::{egui, EguiContexts};
use egui_extras::RetainedImage;
use serde_yaml;
use std::collections::VecDeque;
use std::sync::{Arc, Mutex};
use webbrowser;

#[derive(Resource)]
pub struct Icons {
    pub iot: RetainedImage,
}

impl Default for Icons {
    fn default() -> Self {
        Self {
            iot: RetainedImage::from_svg_bytes("iot", include_bytes!("../assets/iot.svg"))
                .expect("invalid iot.svg"),
        }
    }
}

#[derive(Resource)]
pub struct UiState {
    pub selected: Option<String>,
    pub ai_reply: Option<String>,
    pub dragging: Option<String>,
    pub edit: Option<EditData>,
    pub query: String,
    pub loading: bool,
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
            loading: false,
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

#[derive(Resource, Default)]
pub struct AiTask(pub Option<(Arc<Mutex<std::sync::mpsc::Receiver<reqwest::Result<String>>>>,)>);

pub struct NodeUpdate {
    pub name: String,
    pub description: Option<String>,
    pub story: Option<String>,
    pub calls: Option<Vec<String>>,
    pub used_by: Option<Vec<String>>,
}

#[derive(Resource, Default)]
pub struct NodeInfoTask(pub Option<(NodeUpdate, Arc<Mutex<std::sync::mpsc::Receiver<reqwest::Result<()>>>>)>);

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
    mut node_positions: ResMut<NodePositions>,
    runtime: Res<AsyncRuntime>,
    mut graph_task: ResMut<GraphTask>,
    mut ai_task: ResMut<AiTask>,
    mut node_task: ResMut<NodeInfoTask>,
    icons: Res<Icons>,
) {
    let ctx = contexts.ctx_mut();
    if let Some(rx) = &ai_task.0 {
        if let Ok(res) = rx.0.lock().unwrap().try_recv() {
            ai_task.0 = None;
            if let Ok(text) = res {
                state.ai_reply = Some(text);
            }
        }
    }
    if let Some(pending) = &mut node_task.0 {
        if let Ok(res) = pending.1.lock().unwrap().try_recv() {
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
            if let Some(p) = node_positions.0.get_mut(name) {
                let delta = Vec2::new(pointer_delta.x, pointer_delta.y);
                *p += delta / viewport.zoom;
            }
        } else {
            let delta = Vec2::new(pointer_delta.x, pointer_delta.y);
            viewport.offset += delta;
        }
    } else {
        state.dragging = None;
    }

    egui::CentralPanel::default().show(ctx, |ui| {
        ui.heading("Graph View");
        let rect = ui.max_rect();
        let painter = ui.painter_at(rect);
        let center = rect.center().to_vec2() + viewport.offset;
        // Draw edges using stored node positions
        for node in &data.nodes {
            if let Some(calls) = &node.calls {
                for target in calls {
                    if let (Some(a), Some(b)) = (
                        node_positions.0.get(&node.name),
                        node_positions.0.get(target),
                    ) {
                        painter.line_segment(
                            [
                                egui::pos2(
                                    (center + *a * viewport.zoom).x,
                                    (center + *a * viewport.zoom).y,
                                ),
                                egui::pos2(
                                    (center + *b * viewport.zoom).x,
                                    (center + *b * viewport.zoom).y,
                                ),
                            ],
                            egui::Stroke::new(1.0, egui::Color32::LIGHT_GRAY),
                        );
                    }
                }
            }
        }
        // Draw nodes
        for node in &data.nodes {
            let pos_vec =
                center + *node_positions.0.get(&node.name).unwrap_or(&Vec2::ZERO) * viewport.zoom;
            let pos = egui::pos2(pos_vec.x, pos_vec.y);
            let rect = egui::Rect::from_center_size(pos, egui::vec2(40.0, 40.0));
            let resp = ui.allocate_rect(rect, egui::Sense::click_and_drag());
            if resp.drag_started() {
                state.dragging = Some(node.name.clone());
            }
            let color = if node.node_type.as_deref() == Some("iot") {
                egui::Color32::from_rgb(250, 180, 100)
            } else if state.selected.as_deref() == Some(node.name.as_str()) {
                egui::Color32::LIGHT_BLUE
            } else {
                egui::Color32::from_rgb(100, 150, 250)
            };
            painter.circle_filled(pos, 20.0, color);
            if node.node_type.as_deref() == Some("iot") {
                let size = icons.iot.size_vec2() * 0.5;
                let icon_rect = egui::Rect::from_center_size(pos + egui::vec2(-12.0, -12.0), size);
                egui::Image::from_texture((icons.iot.texture_id(ui.ctx()), size))
                    .paint_at(ui, icon_rect);
            }
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
                            state.popup = Some(if ok {
                                "YAML válido".into()
                            } else {
                                "YAML inválido".into()
                            });
                        }
                    }
                }
                if node.node_type.as_deref() == Some("iot") {
                    if ui.button("Call REST").clicked() {
                        if let Ok(text) = api::call_iot_http(&format!("/iot/{}", node.name)) {
                            state.popup = Some(text);
                        }
                    }
                    if ui.button("Publish MQTT").clicked() {
                        let _ = api::publish_mqtt(&format!("iot/{}", node.name), "ping");
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
            let rx = crate::graph::spawn_graph_request(&runtime, state.query.clone());
            graph_task.0 = Some((rx,));
            state.selected = None;
            state.loading = true;
        }
        if ui.button("Compile").clicked() {
            let rt = runtime.0.clone();
            std::thread::spawn(move || {
                if let Ok((ok, logs)) = rt.block_on(api::compile_project("grafo.yaml")) {
                    for line in logs.lines() {
                        api::push_log(format!("[BUILD] {}", line));
                    }
                    if ok {
                        let _ = webbrowser::open("gen/frontend/index.html");
                    }
                }
            });
        }
        if let Some(name) = &state.selected {
            if ui.button("Compile Module").clicked() {
                let n = name.clone();
                let rt = runtime.0.clone();
                std::thread::spawn(move || {
                    if let Ok((ok, logs)) = rt.block_on(api::compile_module(&n, "grafo.yaml")) {
                        for line in logs.lines() {
                            api::push_log(format!("[BUILD] {}", line));
                        }
                        if ok {
                            let _ = webbrowser::open("gen/frontend/index.html");
                        }
                    }
                });
            }
            if ui.button("Compile Subgraph").clicked() {
                if let Some(yaml) = subgraph_yaml(&data, name) {
                    let rt = runtime.0.clone();
                    std::thread::spawn(move || {
                        if let Ok((ok, logs)) = rt.block_on(api::compile_graph(&yaml)) {
                            for line in logs.lines() {
                                api::push_log(format!("[BUILD] {}", line));
                            }
                            if ok {
                                let _ = webbrowser::open("gen/frontend/index.html");
                            }
                        }
                    });
                }
            }
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
                    ai_task.0 = Some((Arc::new(Mutex::new(rx)),));
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
            ui.label(text.as_str());
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
                ui.horizontal(|ui| {
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
                            node_task.0 = Some((update, Arc::new(Mutex::new(rx))));
                        }
                        state.edit = None;
                    }
                    if ui.button("Cancel").clicked() {
                        state.edit = None;
                    }
                });
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
