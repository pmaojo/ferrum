mod api;
mod app;
mod graph;
mod layout;
mod python;
mod runtime;
mod ui;

use std::io::{BufRead, BufReader};
use std::sync::{mpsc, Arc};

fn main() {
    let (tx, rx) = mpsc::channel::<String>();
    let mut child = python::start_python_service().expect("failed to start python service");

    if let Some(out) = child.stdout.take() {
        let tx_clone = tx.clone();
        std::thread::spawn(move || {
            for line in BufReader::new(out).lines() {
                if let Ok(l) = line {
                    let _ = tx_clone.send(format!("[PY] {l}"));
                }
            }
        });
    }
    if let Some(err) = child.stderr.take() {
        let tx_clone = tx.clone();
        std::thread::spawn(move || {
            for line in BufReader::new(err).lines() {
                if let Ok(l) = line {
                    let _ = tx_clone.send(format!("[PY] {l}"));
                }
            }
        });
    }
    api::set_log_sender(tx.clone());
    let rt = Arc::new(tokio::runtime::Runtime::new().expect("rt"));
    app::run_app(rx, runtime::AsyncRuntime(rt.clone()));
    let _ = child.kill();
}
