use bevy::asset::{io::Reader, AssetLoader, AsyncReadExt, LoadContext};
use bevy::prelude::*;
use bevy::reflect::TypePath;
use bevy::tasks::Task;
use bevy::utils::BoxedFuture;
use bevy_asset_loader::prelude::*;
use bevy_egui::{egui, EguiContexts};
use egui_extras::RetainedImage;
use std::collections::VecDeque;
use thiserror::Error;

pub mod node_factory;
pub mod viewer;

#[derive(Asset, TypePath)]
pub struct SvgImage(pub RetainedImage);

#[derive(Default)]
pub struct SvgImageLoader;

#[derive(Debug, Error)]
pub enum SvgImageLoaderError {
    #[error("Could not read file: {0}")]
    Io(#[from] std::io::Error),
    #[error("Invalid svg: {0}")]
    Svg(String),
}

impl AssetLoader for SvgImageLoader {
    type Asset = SvgImage;
    type Settings = ();
    type Error = SvgImageLoaderError;

    fn load<'a>(
        &'a self,
        reader: &'a mut Reader,
        _settings: &'a Self::Settings,
        load_context: &'a mut LoadContext,
    ) -> BoxedFuture<'a, Result<Self::Asset, Self::Error>> {
        Box::pin(async move {
            let mut bytes = Vec::new();
            reader.read_to_end(&mut bytes).await?;
            let img = RetainedImage::from_svg_bytes(load_context.path().to_string_lossy(), &bytes)
                .map_err(SvgImageLoaderError::Svg)?;
            Ok(SvgImage(img))
        })
    }

    fn extensions(&self) -> &[&str] {
        &["svg"]
    }
}

#[derive(AssetCollection, Resource)]
pub struct Icons {
    #[asset(path = "iot.svg")]
    pub iot: Handle<SvgImage>,
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
