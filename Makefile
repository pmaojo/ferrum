.PHONY: build install run fmt clean

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
