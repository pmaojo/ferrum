# IoT Basic Plugin

This plugin provides a simple starting point for hardware projects. It injects
a few sensor drivers and a telemetry resource so you can start compiling IoT
demos right away.

## Usage

Build the plugin and add it to your project:

```bash
cargo build --release
ferrum add path/to/iot-basic
```

Running `ferrum compile` will now generate the sample drivers and telemetry
setup for you.
