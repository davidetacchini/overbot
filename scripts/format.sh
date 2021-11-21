#!/bin/bash
isort .
black --exclude=env --target-version py310 --line-length=100 .
flake8 .
