.PHONY: help install data ingest dbt-deps dbt-build dbt-test dbt-docs ml app sample-deploy lint test clean

help:
	@echo "make install       — uv sync deps"
	@echo "make data          — download REES46 from Kaggle"
	@echo "make ingest        — CSV → Parquet partitions → DuckDB"
	@echo "make dbt-deps      — install dbt packages"
	@echo "make dbt-build     — dbt seed + run + test"
	@echo "make dbt-test      — dbt test only"
	@echo "make dbt-docs      — generate dbt docs HTML"
	@echo "make ml            — train churn model + score users"
	@echo "make app           — run Streamlit locally"
	@echo "make sample-deploy — build sampled DB for cloud deploy"
	@echo "make lint          — ruff format + check"
	@echo "make test          — pytest"
	@echo "make clean         — remove warehouse + parquet"

install:
	uv sync

data:
	uv run python scripts/download_data.py

ingest:
	uv run python scripts/ingest.py

dbt-deps:
	cd dbt && uv run dbt deps

dbt-build: dbt-deps
	cd dbt && uv run dbt build

dbt-test:
	cd dbt && uv run dbt test

dbt-docs:
	cd dbt && uv run dbt docs generate && uv run dbt docs serve --no-browser --port 8081

ml:
	uv run python -m ml.train_churn

app:
	uv run streamlit run app/Home.py

sample-deploy:
	uv run python scripts/sample_for_deploy.py

lint:
	uv run ruff format .
	uv run ruff check . --fix

test:
	uv run pytest

clean:
	rm -rf warehouse/*.duckdb data/parquet/*
