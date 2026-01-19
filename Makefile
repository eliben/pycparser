.PHONY: check

RUFF_VERSION ?= 0.14.13
RUFF = uvx ruff@$(RUFF_VERSION)

check:
	$(RUFF) check .
	$(RUFF) format .
