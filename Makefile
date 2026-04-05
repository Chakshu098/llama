.PHONY: install test run docker-build docker-run eval lint clean

install:
	pip install -r requirements.txt

test:
	python -m pytest tests/ -v

test-unit:
	python -m pytest tests/test_graders.py -v

test-integration:
	python -m pytest tests/test_integration.py -v

run:
	python -m uvicorn server.app:app --host 0.0.0.0 --port 7861 --reload

docker-build:
	docker build -t incident-response-env .

docker-run:
	docker run -p 7861:7861 --env-file .env incident-response-env

eval:
	@echo "Starting server in background..."
	python -m uvicorn server.app:app --host 0.0.0.0 --port 7861 &
	sleep 3
	python eval/run_eval.py
	@pkill -f "uvicorn server.app" || true

lint:
	python -m py_compile models.py graders.py environment.py scenarios.py server/app.py inference.py
	@echo "All files compile cleanly."

validate-scenarios:
	python scripts/validate_scenario.py

generate-scenario:
	python scripts/generate_scenario.py

clean:
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -name "*.pyc" -delete 2>/dev/null || true
	rm -rf .pytest_cache
