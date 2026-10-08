.PHONY: check format regen-ast test

RUFF_VERSION ?= 0.16.0
RUFF = uvx ruff@$(RUFF_VERSION)

TY_VERSION ?= 0.0.74
TY = uvx ty@$(TY_VERSION)

check:
	$(RUFF) check .
	$(TY) check
	$(MAKE) format

format:
	$(RUFF) format .

regen-ast:
	python3 pycparser/_ast_gen.py
	$(MAKE) format

test:
	python3 -m unittest discover
