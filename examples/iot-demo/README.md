# IoT Demo

Minimal project showcasing the three IoT protocols supported by Ferrum.

```bash
# install ferrum
cargo install --path ../..

# generate code from grafo.yaml
ferrum compile gen/grafo.yaml

# build backend with hardware crates
cargo build -p backend --features hal,rppal,mqtt,ethercat

# run the app
ferrum dev
```
