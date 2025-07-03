use bevy::prelude::*;
use bevy_egui::{EguiContexts, egui};
use bevy::tasks::Task;
use egui_extras::RetainedImage;
use std::collections::VecDeque;

pub mod viewer;

#[derive(Resource)]
pub struct Icons {
    pub iot: RetainedImage,
}

impl Default for Icons {
    fn default() -> Self {
        let iot = match RetainedImage::from_svg_bytes("iot", include_bytes!("../assets/iot.svg")) {
            Ok(img) => img,
            Err(err) => {
                eprintln!("invalid iot.svg: {err}");
                let placeholder = egui::ColorImage::new([1, 1], egui::Color32::WHITE);
                RetainedImage::from_color_image("iot", placeholder)
            }
        };
        Self { iot }
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
pub struct AiTask(pub Option<Task<reqwest::Result<String>>>);

pub struct NodeUpdate {
    pub name: String,
    pub description: Option<String>,
    pub story: Option<String>,
    pub calls: Option<Vec<String>>,
    pub used_by: Option<Vec<String>>,
}

#[derive(Resource, Default)]
pub struct NodeInfoTask(pub Option<(NodeUpdate, Task<reqwest::Result<()>>)>);

#[derive(Resource, Default)]
pub struct BuildTask(pub Option<Task<reqwest::Result<(bool, String)>>>);

pub fn log_panel(
    mut contexts: EguiContexts,
    mut events: EventReader<crate::api::LogEvent>,
    mut logs: ResMut<LogBuffer>,
) {
    for ev in events.read() {
        logs.0.push_back(ev.0.clone());
        if logs.0.len() > 200 {
            logs.0.pop_front();
        }
    }

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
