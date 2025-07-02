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

