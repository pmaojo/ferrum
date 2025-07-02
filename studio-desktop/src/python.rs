use std::path::PathBuf;
use std::process::{Child, Command, Stdio};

pub fn start_python_service() -> std::io::Result<Child> {
    let mut ai_path = PathBuf::from(env!("CARGO_MANIFEST_DIR"));
    ai_path.push("../ai");
    Command::new("uvicorn")
        .current_dir(ai_path)
        .args(["main:app", "--host", "0.0.0.0", "--port", "8000"])
        .stdout(Stdio::piped())
        .stderr(Stdio::piped())
        .spawn()
}
