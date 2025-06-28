.PHONY: build install run fmt clean typeshare-studio typeshare-project

build:
	cargo build

install:
	cargo install --path .

run:
	cargo run -- compile gen/users.yaml

fmt:
	cargo fmt

clean:
	cargo clean

typeshare-studio:
	typeshare --lang=typescript --output-dir studio/src/types shared-models

typeshare-project:
	typeshare --lang=typescript --output-dir projects/\$(PROJECT)/frontend/src/types projects/\$(PROJECT)/shared-models
