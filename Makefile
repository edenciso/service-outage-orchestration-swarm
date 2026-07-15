.PHONY: install run test demo reset

install:
	python -m pip install -e ".[dev]"

run:
	uvicorn outage_swarm.api:app --reload --host 0.0.0.0 --port 8000

test:
	pytest

demo:
	python -m outage_swarm.cli demo cloud-region-retry-storm

reset:
	rm -f data/outage_swarm.db
