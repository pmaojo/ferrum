use bevy::prelude::*;
use bevy_egui::egui;

use crate::graph::Node as GraphNode;
use ferrum_shared_models::NodeType;

use super::{Icons, SvgImage};

pub trait Palette: Send + Sync {
    fn color(&self, node: &GraphNode, selected: bool) -> egui::Color32;
}

pub trait NodeFactory: Send + Sync {
    fn draw_node(
        &self,
        ui: &mut egui::Ui,
        painter: &egui::Painter,
        node: &GraphNode,
        pos: egui::Pos2,
        selected: bool,
        icons: &Icons,
        svg_assets: &Assets<SvgImage>,
    ) -> egui::Response;
}

pub struct DefaultPalette;

impl Palette for DefaultPalette {
    fn color(&self, node: &GraphNode, selected: bool) -> egui::Color32 {
        if node.node_type == NodeType::Iot {
            egui::Color32::from_rgb(250, 180, 100)
        } else if selected {
            egui::Color32::LIGHT_BLUE
        } else {
            egui::Color32::from_rgb(100, 150, 250)
        }
    }
}

pub struct EguiNodeFactory<P: Palette + Send + Sync> {
    palette: P,
}

impl<P: Palette + Send + Sync> EguiNodeFactory<P> {
    pub fn new(palette: P) -> Self {
        Self { palette }
    }
}

impl<P: Palette + Send + Sync> NodeFactory for EguiNodeFactory<P> {
    fn draw_node(
        &self,
        ui: &mut egui::Ui,
        painter: &egui::Painter,
        node: &GraphNode,
        pos: egui::Pos2,
        selected: bool,
        icons: &Icons,
        svg_assets: &Assets<SvgImage>,
    ) -> egui::Response {
        let rect = egui::Rect::from_center_size(pos, egui::vec2(40.0, 40.0));
        let resp = ui.allocate_rect(rect, egui::Sense::click_and_drag());
        let color = self.palette.color(node, selected);
        painter.circle_filled(pos, 20.0, color);

        if node.node_type == NodeType::Iot {
            if let Some(icon) = svg_assets.get(&icons.iot) {
                let size = icon.0.size_vec2() * 0.5;
                let icon_rect = egui::Rect::from_center_size(pos + egui::vec2(-12.0, -12.0), size);
                egui::Image::from_texture((icon.0.texture_id(ui.ctx()), size))
                    .paint_at(ui, icon_rect);
            }
        }

        painter.text(
            pos,
            egui::Align2::CENTER_CENTER,
            &node.id,
            egui::FontId::proportional(14.0),
            egui::Color32::BLACK,
        );
        resp
    }
}

#[derive(Resource)]
pub struct BoxedFactory(pub Box<dyn NodeFactory>);

impl Default for BoxedFactory {
    fn default() -> Self {
        BoxedFactory(Box::new(EguiNodeFactory::new(DefaultPalette)))
    }
}
