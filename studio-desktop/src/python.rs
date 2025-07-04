use std::path::PathBuf;
use std::process::{Child, Command, Stdio};

use crate::api;

pub fn start_python_service() -> std::io::Result<Child> {
    let mut ai_path = PathBuf::from(env!("CARGO_MANIFEST_DIR"));
    ai_path.push("../ai");

    let mut bin = ai_path.join("dist/ai_service");
    if cfg!(windows) {
        bin.set_extension("exe");
    }

    let mut cmd = if bin.exists() {
        let mut c = Command::new(bin);
        c.stdout(Stdio::piped()).stderr(Stdio::piped());
        c
    } else {
        let mut c = Command::new("uvicorn");
        c.current_dir(ai_path)
            .args(["main:app", "--host", "0.0.0.0", "--port", "8001"])
            .stdout(Stdio::piped())
            .stderr(Stdio::piped());
        c
    };

    match cmd.spawn() {
        Ok(child) => Ok(child),
        Err(e) => {
            eprintln!("[PY] failed to launch: {e}");
            Err(e)
        }
    }
}
