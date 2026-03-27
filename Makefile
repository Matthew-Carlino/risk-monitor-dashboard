.PHONY: help install run test lint clean format

help:
	@echo "Risk Monitor Dashboard - Development Commands"
	@echo ""
	@echo "make install    - Install dependencies"
	@echo "make run        - Run Streamlit dashboard"
	@echo "make test       - Run tests with pytest"
	@echo "make lint       - Run code quality checks (flake8)"
	@echo "make format     - Format code with black"
	@echo "make clean      - Clean cache and build files"
	@echo "make demo-data  - Download demo portfolio data"

install:
	pip install -r requirements.txt

run:
	streamlit run app.py

test:
	pytest tests/ -v --tb=short

test-cov:
	pytest tests/ --cov=src --cov-report=html --cov-report=term

lint:
	flake8 src/ app.py --max-line-length=100

format:
	black src/ app.py scripts/ tests/

clean:
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete
	rm -rf .pytest_cache .coverage htmlcov dist/ build/ *.egg-info

demo-data:
	python scripts/generate_demo_data.py

all: install test run
