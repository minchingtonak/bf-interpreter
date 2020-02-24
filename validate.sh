#!/bin/bash

set -Eeuxo pipefail

pydocstyle bf.py
pycodestyle bf.py
pylint -d no-value-for-parameter -d unused-argument -d too-many-instance-attributes -d too-many-arguments bf.py