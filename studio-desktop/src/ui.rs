use bevy::prelude::*;
use bevy_egui::{EguiContexts, egui};
use crate::graph::GraphData;

pub fn graph_viewer(mut contexts: EguiContexts, data: Res<GraphData>) {
    egui::CentralPanel::default().show(contexts.ctx_mut(), |ui| {
        ui.heading("GraphRAG Result");
        ui.add(egui::TextEdit::multiline(&mut data.0.clone()));
    });
}
