use super::{
    node_factory::BoxedFactory, node_factory::NodeFactory, AiTask, BuildTask, EditData, Icons,
    LogBuffer, NodeInfoTask, NodeUpdate, UiState,
};
use super::palette::{self, NodeTemplates};
use crate::api;
use crate::app_state::AppState;
use crate::graph::{GraphData, GraphTask, Node as GraphNode, NodePositions, Viewport};
use ferrum_shared_models::NodeType;
use bevy::prelude::*;
use bevy_egui::{egui, EguiContexts};
use bevy_tokio_tasks::TokioTasksRuntime;
use crate::ui::SvgImage;
use leafwing_input_manager::prelude::*;
use serde_yaml;
use std::collections::HashSet;
use webbrowser;

pub(crate) fn to_egui(v: Vec2) -> egui::Vec2 {
    egui::Vec2::new(v.x, v.y)
}

/// Single onboarding step displayed in the tour overlay.
pub struct TourStep {
    pub title: &'static str,
    pub body: &'static str,
    pub anchor: egui::Align2,
    pub offset: egui::Vec2,
}

/// Resource tracking onboarding progress.
#[derive(Resource)]
pub struct TourState {
    steps: Vec<TourStep>,
    current: usize,
}

impl Default for TourState {
    fn default() -> Self {
        Self {
            steps: vec![
                TourStep {
                    title: "Welcome",
                    body: "Use the controls on the right to generate a graph.",
                    anchor: egui::Align2::RIGHT_TOP,
                    offset: egui::vec2(-10.0, 10.0),
                },
                TourStep {
                    title: "Nodes",
                    body: "Click nodes in the graph to inspect them.",
                    anchor: egui::Align2::CENTER_TOP,
                    offset: egui::vec2(0.0, 10.0),
                },
                TourStep {
                    title: "Logs",
                    body: "Check the bottom panel for build logs and messages.",
                    anchor: egui::Align2::CENTER_BOTTOM,
                    offset: egui::vec2(0.0, -10.0),
                },
            ],
            current: 0,
        }
    }
}

impl TourState {
    pub fn current_step(&self) -> Option<&TourStep> {
        self.steps.get(self.current)
    }

    pub fn advance(&mut self) {
        if self.current < self.steps.len() {
            self.current += 1;
        }
    }

    pub fn index(&self) -> usize {
        self.current
    }
}

fn vibrant_visuals() -> egui::Visuals {
    let mut visuals = egui::Visuals::dark();
    visuals.widgets.active.bg_fill = egui::Color32::from_rgb(0, 150, 255);
    // Brighter background and outline on hover to mimic the previous glow effect
    visuals.widgets.hovered.bg_fill = egui::Color32::from_rgb(80, 80, 120);
    visuals.widgets.hovered.fg_stroke = egui::Stroke::new(1.0, egui::Color32::WHITE);
    visuals.selection.bg_fill = egui::Color32::from_rgb(0, 255, 150);
    visuals.window_fill = egui::Color32::from_rgb(20, 20, 30);
    visuals
}

fn setup_visuals(mut contexts: EguiContexts) {
    if let Ok(ctx) = contexts.ctx_mut() {
        ctx.set_visuals(vibrant_visuals());
    }
}

fn show_tour_overlay(ctx: &egui::Context, tour: &mut TourState) {
    if let Some(step) = tour.current_step() {
        let mut advance = false;
        egui::Window::new(step.title)
            .anchor(step.anchor, step.offset)
            .resizable(false)
            .collapsible(false)
            .show(ctx, |ui| {
                ui.label(step.body);
                if ui.button("Got it").clicked() {
                    advance = true;
                }
            });
        if advance {
            tour.advance();
        }
    }
}

/// Generate YAML for a subgraph rooted at `name`.
pub fn subgraph_yaml(data: &GraphData, id: &str) -> Option<String> {
    let mut names = HashSet::new();
    let node = data.nodes.iter().find(|n| n.id == id)?;
    names.insert(id.to_string());
    for c in &node.depends_on {
        names.insert(c.clone());
    }
    for n in &data.nodes {
        if n.depends_on.iter().any(|d| d == &node.id) {
            names.insert(n.id.clone());
        }
    }
    let nodes: Vec<GraphNode> = data
        .nodes
        .iter()
        .filter(|n| names.contains(&n.id))
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
    action_state_query: Query<&ActionState<crate::input::Action>>,
) {
    let ctx = match contexts.ctx_mut() {
        Ok(ctx) => ctx,
        Err(_) => return,
    };
    let action_state = match action_state_query.get_single() {
        Ok(state) => state,
        Err(_) => return,
    };
    let pointer_delta = ctx.input(|i| i.pointer.delta());
    let zoom_delta = action_state.value(&crate::input::Action::Zoom);
    if zoom_delta != 0.0 {
        viewport.zoom = (viewport.zoom + zoom_delta * 0.1).clamp(0.2, 5.0);
    }
    if action_state.pressed(&crate::input::Action::Pan) {
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

fn poll_ai_task(ai_task: &mut AiTask, state: &mut UiState) {
    if let Some(handle) = ai_task.0.as_mut() {
        if let Some(res) = futures_lite::future::block_on(futures_lite::future::poll_once(handle)) {
            ai_task.0 = None;
            match res {
                Ok(res) => {
                    if let Ok(text) = res {
                        state.ai_reply = Some(text);
                    } else {
                        // TODO: surface the request failure to the UI
                    }
                }
                Err(err) => {
                    // TODO: surface the join error to the UI
                    eprintln!("AI task join error: {err}");
                }
            }
        }
    }
}

fn poll_node_task(node_task: &mut NodeInfoTask, data: &mut GraphData) {
    if let Some((update, handle)) = node_task.0.as_mut() {
        if let Some(res) = futures_lite::future::block_on(futures_lite::future::poll_once(handle)) {
            if res.is_ok() {
                if let Some(node) = data.nodes.iter_mut().find(|n| n.id == update.id) {
                    node.description = update.description.clone();
                    node.story = update.story.clone();
                    if let Some(dep) = update.depends_on.clone() {
                        node.depends_on = dep;
                    }
                }
            }
            node_task.0 = None;
        }
    }
}

fn draw_edges(
    painter: &egui::Painter,
    nodes: &[GraphNode],
    node_positions: &NodePositions,
    center: egui::Vec2,
    viewport: &Viewport,
) {
    for node in nodes {
        for target in &node.depends_on {
            if let (Some(a), Some(b)) = (
                node_positions.0.get(&node.id),
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

#[allow(clippy::too_many_arguments)]
fn draw_nodes(
    ui: &mut egui::Ui,
    painter: &egui::Painter,
    data: &mut GraphData,
    state: &mut UiState,
    node_positions: &mut NodePositions,
    center: egui::Vec2,
    viewport: &Viewport,
    factory: &dyn NodeFactory,
    icons: &Icons,
    svg_assets: &Assets<SvgImage>,
    mut log_writer: &mut EventWriter<crate::api::LogEvent>,
    runtime: &TokioTasksRuntime,
    node_task: &mut NodeInfoTask,
) {
    for node in &data.nodes {
        let pos_vec = center
            + to_egui(*node_positions.0.get(&node.id).unwrap_or(&Vec2::ZERO)) * viewport.zoom;
        let pos = egui::pos2(pos_vec.x, pos_vec.y);
        let selected = state.selected.as_deref() == Some(node.id.as_str());
        let resp = factory.draw_node(ui, painter, node, pos, selected, icons, svg_assets);
        if resp.drag_started() {
            state.dragging = Some(node.id.clone());
        }
        if resp.hovered() {
            if let Some(desc) = &node.description {
                egui::show_tooltip_at_pointer(
                    ui.ctx(),
                    ui.layer_id(),
                    egui::Id::new(format!("tip_{}", node.id)),
                    |ui| {
                        ui.label(desc);
                    },
                );
            }
        }
        if resp.clicked() {
            state.selected = Some(node.id.clone());
            state.ai_reply = None;
        }
        resp.context_menu(|ui| {
            if ui.button("Edit info").clicked() {
                state.edit = Some(EditData {
                    id: node.id.clone(),
                    description: node.description.clone().unwrap_or_default(),
                    story: node.story.clone().unwrap_or_default(),
                    depends_on: node.depends_on.join(", "),
                });
            }
            if ui.button("Simulate").clicked() {
                if let Some(yaml) = subgraph_yaml(data, &node.id) {
                    if let Ok(text) = api::simulate_flow(&mut log_writer, &yaml) {
                        state.popup = Some(text);
                    }
                }
            }
            if ui.button("Generate").clicked() {
                if let Ok(yaml) = api::generate_component(&mut log_writer, &node.id) {
                    state.popup = Some(yaml);
                }
            }
            if ui.button("Validate").clicked() {
                if let Some(yaml) = subgraph_yaml(data, &node.id) {
                    if let Ok(ok) = api::validate_yaml(&mut log_writer, &yaml) {
                        state.popup = Some(if ok {
                            "YAML válido".into()
                        } else {
                            "YAML inválido".into()
                        });
                    }
                }
            }
            if node.node_type == NodeType::Iot {
                if ui.button("Call REST").clicked() {
                    if let Ok(text) =
                        api::call_iot_http(&mut log_writer, &format!("/iot/{}", node.id))
                    {
                        state.popup = Some(text);
                    }
                }
                if ui.button("Publish MQTT").clicked() {
                    let _ =
                        api::publish_mqtt(&mut log_writer, &format!("iot/{}", node.id), "ping");
                }
            }
        });
    }
}

fn show_popup(ctx: &egui::Context, state: &mut UiState) {
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
}

#[allow(clippy::too_many_arguments)]
fn show_edit_window(
    ctx: &egui::Context,
    data: &mut GraphData,
    state: &mut UiState,
    runtime: &TokioTasksRuntime,
    node_task: &mut NodeInfoTask,
) {
    if let Some(mut edit_data) = state.edit.take() {
        let mut close = false;
        egui::Window::new(format!("Edit {}", edit_data.id))
            .collapsible(false)
            .show(ctx, |ui| {
                ui.label("Description");
                ui.text_edit_singleline(&mut edit_data.description);
                ui.label("Story");
                ui.text_edit_multiline(&mut edit_data.story);
                ui.label("Depends on (comma separated)");
                ui.text_edit_singleline(&mut edit_data.depends_on);
                ui.horizontal(|ui| {
                    if ui.button("Save").clicked() {
                        if let Some(node) = data.nodes.iter().find(|n| n.id == edit_data.id) {
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
                                id: node.id.clone(),
                                description: desc.clone(),
                                story: story.clone(),
                                depends_on: if edit_data.depends_on.trim().is_empty() {
                                    None
                                } else {
                                    Some(
                                        edit_data
                                            .depends_on
                                            .split(',')
                                            .map(|s| s.trim().to_string())
                                            .collect(),
                                    )
                                },
                            };
                            let name = update.id.clone();
                            let desc_clone = update.description.clone();
                            let story_clone = update.story.clone();
                            let handle = runtime.runtime().spawn(async move {
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

/// Draw nodes and edges of the graph.
#[allow(clippy::too_many_arguments)]
pub fn draw_graph(
    mut contexts: EguiContexts,
    mut data: ResMut<GraphData>,
    mut state: ResMut<UiState>,
    viewport: Res<Viewport>,
    mut node_positions: ResMut<NodePositions>,
    runtime: Res<TokioTasksRuntime>,
    mut graph_task: ResMut<GraphTask>,
    mut ai_task: ResMut<AiTask>,
    mut node_task: ResMut<NodeInfoTask>,
    mut log_writer: EventWriter<crate::api::LogEvent>,
    factory: Res<BoxedFactory>,
    icons: Option<Res<Icons>>,
    svg_assets: Res<Assets<SvgImage>>,
    mut tour: ResMut<TourState>,
) {
    let Some(icons) = icons else { return; };
    if let Ok(ctx) = contexts.ctx_mut() {
        poll_ai_task(&mut ai_task, &mut state);
        poll_node_task(&mut node_task, &mut data);
        egui::CentralPanel::default().show(ctx, |ui| {
            ui.heading("Graph View");
            let rect = ui.max_rect();
            let painter = ui.painter_at(rect);
            let center = rect.center().to_vec2() + to_egui(viewport.offset);
            draw_edges(&painter, &data.nodes, &node_positions, center, &viewport);
        draw_nodes(
            ui,
            &painter,
            &mut data,
            &mut state,
            &mut node_positions,
            center,
            &viewport,
            factory.0.as_ref(),
            &icons,
            &svg_assets,
            &mut log_writer,
            &runtime,
            &mut node_task,
        );
            palette::handle_drop(ctx, rect, &viewport, &mut state, &mut data, &mut node_positions);
        });
        show_popup(ctx, &mut state);
        show_edit_window(ctx, &mut data, &mut state, &runtime, &mut node_task);
        show_tour_overlay(ctx, &mut tour);
    }
}

/// Update the side panel with controls.
#[allow(clippy::too_many_arguments)]
pub fn update_side_panel(
    mut contexts: EguiContexts,
    mut data: ResMut<GraphData>,
    mut state: ResMut<UiState>,
    runtime: Res<TokioTasksRuntime>,
    mut graph_task: ResMut<GraphTask>,
    mut ai_task: ResMut<AiTask>,
    mut log_writer: EventWriter<crate::api::LogEvent>,
    mut build_task: ResMut<BuildTask>,
) {
    let ctx = match contexts.ctx_mut() {
        Ok(ctx) => ctx,
        Err(_) => return,
    };
    let mut writer_opt = Some(log_writer);
    egui::SidePanel::right("side_panel").show(ctx, |ui| {
        ui.heading("Graph Controls");
        ui.label("Question");
        ui.text_edit_singleline(&mut state.query);
        if ui.button("Regenerate").clicked() {
            let _writer = writer_opt.take().unwrap();
            let handle = crate::graph::spawn_graph_request(&runtime, state.query.clone());
            graph_task.0 = Some(handle);
            state.selected = None;
            state.loading = true;
        }
        if ui.button("Compile").clicked() {
            let handle = runtime.spawn_background_task(move |_| async move { api::compile_project("grafo.yaml").await });
            build_task.0 = Some(handle);
        }
        if let Some(name) = &state.selected {
            if ui.button("Compile Module").clicked() {
                let n = name.clone();
                let handle =
                    runtime.spawn_background_task(move |_| async move { api::compile_module(&n, "grafo.yaml").await });
                build_task.0 = Some(handle);
            }
            if ui.button("Compile Subgraph").clicked() {
                if let Some(yaml) = subgraph_yaml(&data, name) {
                    let handle = runtime.spawn_background_task(move |_| async move { api::compile_graph(&yaml).await });
                    build_task.0 = Some(handle);
                }
            }
        }
        if state.loading {
            ui.add(egui::Spinner::new());
        }
        ui.separator();
        if let Some(name) = &state.selected {
            if let Some(node) = data.nodes.iter().find(|n| &n.id == name) {
                ui.label(format!("Selected: {}", name));
                if let Some(story) = &node.story {
                    egui::CollapsingHeader::new("Story").show(ui, |ui| {
                        ui.label(story);
                    });
                }
                if ui.button("Ask AI Team").clicked() {
                    let question = format!("What affects {}?", name);
                    let handle = runtime.spawn_background_task(move |_| async move {
                        api::ask_ai_team(&question).await
                    });
                    ai_task.0 = Some(handle);
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
        if let Some(res) =
            futures_lite::future::block_on(futures_lite::future::poll_once(handle))
        {
            task.0 = None;
            match res {
                Ok(Ok((ok, logs))) => {
                    for line in logs.lines() {
                        writer.send(crate::api::LogEvent(format!("[BUILD] {}", line)));
                    }
                    if ok {
                        let _ = webbrowser::open("gen/frontend/index.html");
                    }
                }
                Ok(Err(err)) => {
                    writer.send(crate::api::LogEvent(format!("Build error: {err}")));
                }
                Err(err) => {
                    writer.send(crate::api::LogEvent(format!(
                        "Task join error: {err}"
                    )));
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
            .init_resource::<TourState>()
            .init_resource::<NodeTemplates>()
            .init_resource::<BoxedFactory>()
            .init_resource::<BuildTask>()
            .add_plugins(crate::runtime::runtime_plugin())
            .insert_resource(AiTask::default())
            .insert_resource(NodeInfoTask::default())
            .insert_resource(LogBuffer::default())
            .add_systems(Startup, setup_visuals)
            .add_systems(OnEnter(AppState::Loading), crate::graph::load_graph)
            .add_systems(Update, crate::graph::update_graph_task)
            .add_systems(
                Update,
                (
                    handle_interaction,
                    draw_graph.run_if(resource_exists::<Icons>()),
                    palette::node_palette,
                    update_side_panel,
                    update_build_task,
                    super::log_panel,
                )
                    .run_if(in_state(AppState::InGame)),
            );
    }
}
