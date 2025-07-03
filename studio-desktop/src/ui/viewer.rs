use super::{AiTask, BuildTask, EditData, Icons, NodeInfoTask, NodeUpdate, UiState, LogBuffer};
use crate::app_state::AppState;
use crate::api;
use crate::graph::{GraphData, GraphTask, Node, NodePositions, Viewport};
use bevy::prelude::*;
use bevy_egui::{egui, EguiContexts};
use bevy_tokio_tasks::tokio::task::JoinHandle;
use bevy_tokio_tasks::TokioTasksRuntime as AsyncRuntime;
use serde_yaml;
use std::collections::HashSet;
use webbrowser;

fn to_egui(v: Vec2) -> egui::Vec2 {
    egui::Vec2::new(v.x, v.y)
}

/// Generate YAML for a subgraph rooted at `name`.
pub fn subgraph_yaml(data: &GraphData, name: &str) -> Option<String> {
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

/// Handle user input like dragging and zooming.
pub fn handle_interaction(
    mut contexts: EguiContexts,
    mut viewport: ResMut<Viewport>,
    mut node_positions: ResMut<NodePositions>,
    mut state: ResMut<UiState>,
) {
    let ctx = contexts.ctx_mut();
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
}

/// Draw nodes and edges of the graph.
#[allow(clippy::too_many_arguments)]
pub fn draw_graph(
    mut contexts: EguiContexts,
    mut data: ResMut<GraphData>,
    mut state: ResMut<UiState>,
    viewport: Res<Viewport>,
    mut node_positions: ResMut<NodePositions>,
    runtime: Res<AsyncRuntime>,
    mut graph_task: ResMut<GraphTask>,
    mut ai_task: ResMut<AiTask>,
    mut node_task: ResMut<NodeInfoTask>,
    mut log_writer: EventWriter<crate::api::LogEvent>,
    icons: Res<Icons>,
) {
    let ctx = contexts.ctx_mut();
    if let Some(handle) = ai_task.0.as_mut() {
        if let Some(res) = futures_lite::future::block_on(futures_lite::future::poll_once(handle)) {
            ai_task.0 = None;
            if let Ok(text) = res {
                state.ai_reply = Some(text);
            }
        }
    }
    let mut clear = false;
    if let Some((update, handle)) = node_task.0.as_mut() {
        if let Some(res) = futures_lite::future::block_on(futures_lite::future::poll_once(handle)) {
            if res.is_ok() {
                if let Some(node) = data.nodes.iter_mut().find(|n| n.name == update.name) {
                    node.description = update.description.clone();
                    node.story = update.story.clone();
                    node.calls = update.calls.clone();
                    node.used_by = update.used_by.clone();
                }
            }
            clear = true;
        }
    }
    if clear {
        node_task.0 = None;
    }
    egui::CentralPanel::default().show(ctx, |ui| {
        ui.heading("Graph View");
        let rect = ui.max_rect();
        let painter = ui.painter_at(rect);
        let center = rect.center().to_vec2() + to_egui(viewport.offset);
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
                                    (center + to_egui(*a) * viewport.zoom).x,
                                    (center + to_egui(*a) * viewport.zoom).y,
                                ),
                                egui::pos2(
                                    (center + to_egui(*b) * viewport.zoom).x,
                                    (center + to_egui(*b) * viewport.zoom).y,
                                ),
                            ],
                            egui::Stroke::new(1.0, egui::Color32::LIGHT_GRAY),
                        );
                    }
                }
            }
        }
        for node in &data.nodes {
            let pos_vec = center
                + to_egui(*node_positions.0.get(&node.name).unwrap_or(&Vec2::ZERO)) * viewport.zoom;
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
                        if let Ok(text) = api::simulate_flow(&mut log_writer, &yaml) {
                            state.popup = Some(text);
                        }
                    }
                }
                if ui.button("Generate").clicked() {
                    if let Ok(yaml) = api::generate_component(&mut log_writer, &node.name) {
                        state.popup = Some(yaml);
                    }
                }
                if ui.button("Validate").clicked() {
                    if let Some(yaml) = subgraph_yaml(&data, &node.name) {
                        if let Ok(ok) = api::validate_yaml(&mut log_writer, &yaml) {
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
                        if let Ok(text) = api::call_iot_http(&mut log_writer, &format!("/iot/{}", node.name)) {
                            state.popup = Some(text);
                        }
                    }
                    if ui.button("Publish MQTT").clicked() {
                        let _ = api::publish_mqtt(&mut log_writer, &format!("iot/{}", node.name), "ping");
                    }
                }
            });
        }
    });
    if let Some(text_val) = state.popup.clone() {
        let mut close = false;
        egui::Window::new("Result").show(ctx, |ui| {
            ui.label(text_val.as_str());
            if ui.button("Close").clicked() {
                close = true;
            }
        });
        if close {
            state.popup = None;
        }
    }
    if let Some(mut edit_data) = state.edit.take() {
        let mut close = false;
        egui::Window::new(format!("Edit {}", edit_data.name))
            .collapsible(false)
            .show(ctx, |ui| {
                ui.label("Description");
                ui.text_edit_singleline(&mut edit_data.description);
                ui.label("Story");
                ui.text_edit_multiline(&mut edit_data.story);
                ui.label("Calls (comma separated)");
                ui.text_edit_singleline(&mut edit_data.calls);
                ui.label("Used by (comma separated)");
                ui.text_edit_singleline(&mut edit_data.used_by);
                ui.horizontal(|ui| {
                    if ui.button("Save").clicked() {
                        if let Some(node) = data.nodes.iter().find(|n| n.name == edit_data.name) {
                            let desc = if edit_data.description.trim().is_empty() {
                                None
                            } else {
                                Some(edit_data.description.clone())
                            };
                            let story = if edit_data.story.trim().is_empty() {
                                None
                            } else {
                                Some(edit_data.story.clone())
                            };
                            let update = NodeUpdate {
                                name: node.name.clone(),
                                description: desc.clone(),
                                story: story.clone(),
                                calls: if edit_data.calls.trim().is_empty() {
                                    None
                                } else {
                                    Some(
                                        edit_data
                                            .calls
                                            .split(',')
                                            .map(|s| s.trim().to_string())
                                            .collect(),
                                    )
                                },
                                used_by: if edit_data.used_by.trim().is_empty() {
                                    None
                                } else {
                                    Some(
                                        edit_data
                                            .used_by
                                            .split(',')
                                            .map(|s| s.trim().to_string())
                                            .collect(),
                                    )
                                },
                            };
                            let name = update.name.clone();
                            let desc_clone = update.description.clone();
                            let story_clone = update.story.clone();
                            let handle = runtime.spawn(async move {
                                api::store_node_info(
                                    &name,
                                    desc_clone.as_deref(),
                                    story_clone.as_deref(),
                                )
                                .await
                            });
                            node_task.0 = Some((update, handle));
                        }
                        close = true;
                    }
                    if ui.button("Cancel").clicked() {
                        close = true;
                    }
                });
            });
        if !close {
            state.edit = Some(edit_data);
        }
    }
}

/// Update the side panel with controls.
#[allow(clippy::too_many_arguments)]
pub fn update_side_panel(
    mut contexts: EguiContexts,
    mut data: ResMut<GraphData>,
    mut state: ResMut<UiState>,
    runtime: Res<AsyncRuntime>,
    mut graph_task: ResMut<GraphTask>,
    mut ai_task: ResMut<AiTask>,
    mut log_writer: EventWriter<crate::api::LogEvent>,
    mut build_task: ResMut<BuildTask>,
) {
    let ctx = contexts.ctx_mut();
    let mut writer_opt = Some(log_writer);
    egui::SidePanel::right("side_panel").show(ctx, |ui| {
        ui.heading("Graph Controls");
        ui.label("Question");
        ui.text_edit_singleline(&mut state.query);
        if ui.button("Regenerate").clicked() {
            let writer = writer_opt.take().unwrap();
            let handle = crate::graph::spawn_graph_request(&runtime, state.query.clone(), writer);
            graph_task.0 = Some(handle);
            state.selected = None;
            state.loading = true;
        }
        if ui.button("Compile").clicked() {
            let handle = runtime.spawn(async move { api::compile_project("grafo.yaml").await });
            build_task.0 = Some(handle);
        }
        if let Some(name) = &state.selected {
            if ui.button("Compile Module").clicked() {
                let n = name.clone();
                let handle = runtime.spawn(async move {
                    api::compile_module(&n, "grafo.yaml").await
                });
                build_task.0 = Some(handle);
            }
            if ui.button("Compile Subgraph").clicked() {
                if let Some(yaml) = subgraph_yaml(&data, name) {
                    let handle = runtime.spawn(async move {
                        api::compile_graph(&yaml).await
                    });
                    build_task.0 = Some(handle);
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
                    if let Some(writer) = writer_opt.take() {
                        let handle = runtime.spawn_background_task(move |_| async move {
                            let mut w = writer;
                            api::ask_ai_team(&mut w, &question).await
                        });
                        ai_task.0 = Some(handle);
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

pub fn update_build_task(
    mut task: ResMut<BuildTask>,
    mut writer: EventWriter<crate::api::LogEvent>,
) {
    if let Some(handle) = task.0.as_mut() {
        if let Some(res) = futures_lite::future::block_on(futures_lite::future::poll_once(handle)) {
            task.0 = None;
            if let Ok((ok, logs)) = res {
                for line in logs.lines() {
                    writer.send(crate::api::LogEvent(format!("[BUILD] {}", line)));
                }
                if ok {
                    let _ = webbrowser::open("gen/frontend/index.html");
                }
            }
        }
    }
}

/// Bevy plugin bundling all graph viewer systems and resources.
pub struct ViewerPlugin;

impl Plugin for ViewerPlugin {
    fn build(&self, app: &mut App) {
        app.add_event::<crate::api::LogEvent>()
            .init_resource::<GraphData>()
            .init_resource::<NodePositions>()
            .init_resource::<Viewport>()
            .init_resource::<GraphTask>()
            .init_resource::<UiState>()
            .init_resource::<Icons>()
            .init_resource::<BuildTask>()
            .insert_resource(AsyncRuntime::default())
            .insert_resource(AiTask::default())
            .insert_resource(NodeInfoTask::default())
            .insert_resource(LogBuffer::default())
            .add_systems(OnEnter(AppState::Loading), crate::graph::load_graph)
            .add_systems(Update, crate::graph::update_graph_task)
            .add_systems(
                Update,
                (
                    handle_interaction,
                    draw_graph,
                    update_side_panel,
                    update_build_task,
                    super::log_panel,
                )
                    .run_if(in_state(AppState::InGame)),
            );
    }
}
