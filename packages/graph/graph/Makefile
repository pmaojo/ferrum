.PHONY: install start-services test lint docs

install:
	pip install -e .[dev]

start-services:
	docker compose up -d gremlin-server
	bash scripts/setup_falkordb.sh
	docker run -d --name memgraph -p 7687:7687 -p 3000:3000 memgraph/memgraph-platform:latest
	echo Done

test:
	pytest -q

lint:
	flake8

docs:
	bash scripts/generate_docs.sh
