# IoT Basic Plugin

This optional plugin injects two sample sensor drivers and a telemetry resource.
It enables the `mqtt` feature so your project pulls in the MQTT helpers.

## Usage

```bash
ferrum add path/to/iot-basic
ferrum compile grafo.yaml
```

After compilation you'll find `backend/iot/read_temperature.rs` and
`backend/iot/read_humidity.rs` plus stub code under `backend/resources/telemetry.rs`.
