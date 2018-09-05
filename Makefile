MAKEFLAGS += --warn-undefined-variables --no-print-directory
SHELL := bash
.ONESHELL:
.SHELLFLAGS := -eu -o pipefail -c
.DEFAULT_GOAL := help

# COLORS
GREEN  := $(shell tput -Txterm setaf 2)
YELLOW := $(shell tput -Txterm setaf 3)
WHITE  := $(shell tput -Txterm setaf 7)
RESET  := $(shell tput -Txterm sgr0)

.PHONY: help deps plugins clean

HELP_PADDING = 10
## Display this help
help:
	@echo 'Usage:'
	@echo '  ${YELLOW}make${RESET} ${GREEN}<target>${RESET}'
	@echo ''
	@echo 'Targets:'
	@awk '/^[a-zA-Z\-\_0-9]+:/ { \
		helpMessage = match(lastLine, /^## (.*)/); \
		if (helpMessage) { \
			helpCommand = substr($$1, 0, index($$1, ":")-1); \
			helpMessage = substr(lastLine, RSTART + 3, RLENGTH); \
			printf "  ${YELLOW}%-$(HELP_PADDING)s${RESET} ${GREEN}%s${RESET}\n", helpCommand, helpMessage; \
		} \
	} \
	{ lastLine = $$0 }' $(MAKEFILE_LIST)

## Install dependencies for this project
deps: clean
	pip install -r requirements.txt

## Copy plugins file to TARGET= sceptre project
plugins:
ifeq (, $(TARGET))
	$(error Please specity TARGET= value)
endif
	/bin/test -d "$(TARGET)/hooks" || mkdir -p "$(TARGET)/hooks"
	/bin/test -d "$(TARGET)/resolvers" || mkdir -p "$(TARGET)/resolvers"
	/bin/cp -f hooks/s3_package.py "$(TARGET)/hooks/"
	/bin/cp -f resolvers/s3_version.py "$(TARGET)/resolvers/"

## Clean temporary artifacts
clean:
	@ rm -rf build/ dist/ *.egg-info/
	@ find . -name "*.py[cod]" -delete
	@ find . -name "__pycache__" -print0 | xargs -0 rm -rf
