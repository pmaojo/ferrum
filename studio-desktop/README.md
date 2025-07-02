# 🖥 Ferrum Studio Desktop

This crate provides a native desktop version of the Ferrum Studio built with Bevy and egui. It lets you visualize and explore your architecture graph without running a separate web environment.

## Running

```bash
cargo run -p studio-desktop
```

The desktop binary automatically starts the Python backend from the `ai/` directory before launching the UI and stops it when you exit.

