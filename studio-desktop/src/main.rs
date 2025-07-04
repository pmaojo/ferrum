mod api;
mod app;
mod graph;
mod layout;
mod python;
mod runtime;
mod input;

mod ui;
mod app_state;

use std::io::{BufRead, BufReader};
use std::sync::mpsc;

fn main() -> std::io::Result<()> {
    let (tx, rx) = mpsc::channel::<String>();
    let mut child = match python::start_python_service() {
        Ok(child) => child,
        Err(e) => {
            eprintln!("failed to start python service: {e}");
            return Err(e);
        }
    };

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
    app::run_app(rx);
    let _ = child.kill();
    Ok(())
}
