#!/bin/bash
isort .
black --exclude=env --line-length=100 .
flake8 .
