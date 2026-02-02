.PHONY: venv install clean
VENV=.venv
ifeq ($(OS),Windows_NT)
    PY=py
    PIP=$(VENV)/Scripts/pip.exe
    RM=cmd /c rmdir /s /q
else
    PY=python3
    PIP=$(VENV)/bin/pip
    RM=rm -rf
endif

venv:
	$(PY) -m venv $(VENV)
	$(PIP) install -U pip setuptools wheel

install:
	$(PIP) install -e .

clean:
	$(RM) $(VENV)
