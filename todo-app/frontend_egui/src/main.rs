mod app;
mod state;
mod navigation;
mod views;
mod forms;
mod api;

use app::App;

fn main() -> Result<(), eframe::Error> {
    let options = eframe::NativeOptions {
        viewport: egui::ViewportBuilder::default()
            .with_inner_size([1024.0, 768.0]),
        ..Default::default()
    };
    
    eframe::run_native(
        "Ferrum Todo App",
        options,
        Box::new(|cc| Box::new(App::new(cc))),
    )
}
