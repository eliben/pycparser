.PHONY: check test

RUFF_VERSION ?= 0.15.12
RUFF = uvx ruff@$(RUFF_VERSION)

TY_VERSION ?= 0.0.33
TY = uvx ty@$(TY_VERSION)

check:
	$(RUFF) check .
	$(TY) check
	$(RUFF) format .

test:
	python3 -m unittest discover
