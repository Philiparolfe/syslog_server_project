# Makefile for Capstone Project

VENV_DIR := .venv
PYTHON := $(VENV_DIR)/bin/python
PIP := $(VENV_DIR)/bin/pip
REQ := requirements.txt
STARTUP_SCRIPT := start.sh

.PHONY: help venv install run clean

help:
	@echo "Available commands:"
	@echo "  make venv      - Create virtual environment in .venv/"
	@echo "  make install   - Install dependencies from requirements.txt"
	@echo "  make run       - Run the full system (sudo if required)"
	@echo "  make clean     - Delete the virtual environment"

venv:
	@if [ ! -d "$(VENV_DIR)" ]; then \
		echo "Creating virtual environment..."; \
		python3 -m venv $(VENV_DIR); \
	else \
		echo "Virtual environment already exists."; \
	fi

install: venv
	@echo "Installing dependencies..."
	$(PIP) install --upgrade pip
	$(PIP) install -r $(REQ)

run: install
	@echo "Starting the project using $(STARTUP_SCRIPT)..."
	sudo ./$(STARTUP_SCRIPT)

clean:
	@echo "Cleaning up virtual environment..."
	rm -rf $(VENV_DIR)
