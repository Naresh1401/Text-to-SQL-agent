.PHONY: install setup-db run test

install:
	pip install -r requirements.txt

setup-db:
	python data/setup_db.py

run:
	uvicorn src.api.main:app --host 0.0.0.0 --port 8000 --reload

test:
	python tests/test_text2sql.py
