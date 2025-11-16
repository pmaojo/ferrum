.PHONY: build install run fmt clean typeshare-project
.PHONY: ai-setup ai-dev ai-build studio-desktop

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


typeshare-project:
typeshare --lang=typescript --output-dir projects/\$(PROJECT)/frontend/src/types projects/\$(PROJECT)/shared-models

ai-setup:
        cd ai && python -m pip install -r requirements.txt

ai-dev:
        cd ai && uvicorn main:app --reload --host 0.0.0.0 --port 8001

ai-build:
	cd ai && ./build_binary.sh


studio-desktop:
        cargo run -p studio-desktop
