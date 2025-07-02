mod app;
mod python;

fn main() {
    let mut child = python::start_python_service().expect("failed to start python service");
    app::run_app();
    let _ = child.kill();
}
