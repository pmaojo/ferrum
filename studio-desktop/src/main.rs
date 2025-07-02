mod app;
mod python;
mod api;
mod graph;
mod layout;
mod ui;

fn main() {
    let mut child = python::start_python_service().expect("failed to start python service");
    app::run_app();
    let _ = child.kill();
}
