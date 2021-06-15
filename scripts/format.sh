#!/bin/bash
isort .
black --exclude=env --line-length=88 .
flake8 .
