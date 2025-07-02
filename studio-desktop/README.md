# Studio Desktop

This crate contains the Bevy-based desktop version of Ferrum Studio.
It launches the Python backend automatically and connects to the `/graph-rag` and `/ai-team` endpoints.

# 🖥 Ferrum Studio Desktop

This crate provides a native desktop version of the Ferrum Studio built with Bevy and egui. It lets you visualize and explore your architecture graph without running a separate web environment.

## Running

```bash
cargo run -p studio-desktop
```

## Graph Viewer Controls

- **Zoom** with the mouse wheel or trackpad pinch.
- **Pan** by dragging with the primary mouse button.

See [docs/studio-desktop.md](../docs/studio-desktop.md) for more details.


The desktop binary automatically starts the Python backend from the `ai/` directory before launching the UI and stops it when you exit.

