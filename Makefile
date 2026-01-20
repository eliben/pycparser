.PHONY: check

RUFF_VERSION ?= 0.14.13
RUFF = uvx ruff@$(RUFF_VERSION)

TY_VERSION ?= 0.0.12
TY = uvx ty@$(TY_VERSION)

check:
	$(RUFF) check .
	$(TY) check
	$(RUFF) format .
