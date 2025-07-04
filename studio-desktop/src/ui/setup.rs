use bevy::prelude::*;
use bevy_egui::{egui, EguiContexts};

use crate::{app_state::AppState, settings::ProjectSettings};

/// Display an initial dialog for selecting the `grafo.yaml` file.
pub fn setup_panel(
    mut contexts: EguiContexts,
    mut settings: ResMut<ProjectSettings>,
    mut next_state: ResMut<NextState<AppState>>,
) {
    if settings.confirmed {
        return;
    }

    if let Ok(ctx) = contexts.ctx_mut() {
        egui::CentralPanel::default().show(ctx, |ui| {
            ui.vertical_centered(|ui| {
                ui.heading("Load grafo.yaml");
                ui.label("Path to grafo.yaml");
                ui.text_edit_singleline(&mut settings.grafo_path);
                if ui.button("Continue").clicked() && !settings.grafo_path.is_empty() {
                    settings.confirmed = true;
                    next_state.set(AppState::Loading);
                }
            });
        });
    }
}
