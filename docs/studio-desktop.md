# Studio Desktop

The `studio-desktop` crate contains the Bevy-based desktop version of Ferrum's Studio.
It starts the Python backend automatically and connects to the `/graph-rag` and `/ai-team` endpoints.

```
ferrum/
├── studio-desktop/
│   ├── Cargo.toml
│   └── src/
```

Run the application with:

```bash
cargo run -p studio-desktop
```

### NodePositions resource

The viewer keeps the coordinates of each graph node in a Bevy resource named
`NodePositions`. It maps node names to `Vec2` values and is initialized on
startup so UI systems can read and modify the layout.

### Distribution

The release zip for the desktop app bundles the `ai_service` binary built with
PyInstaller under `ai/dist/`. This means the Python environment is no longer
required on the target machine to run Ferrum Studio.

### Architecture

`ViewerPlugin` groups the graph viewer systems and resources. Node rendering is
handled by a pluggable `NodeFactory` trait. A `Palette` implementation determines
the color of each node. The default `EguiNodeFactory` uses `egui` widgets and the
`DefaultPalette` for styling, allowing alternative factories or palettes to be
swapped in without changing the viewer logic.

