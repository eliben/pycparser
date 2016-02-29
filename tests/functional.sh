#!/bin/bash

# quick functional test of one of the most popular stacks relying on
# pycarser; cryptography -> cffi -> pycparser

if [ "$TRAVIS_PYTHON_VERSION" = "3.2" ]; then
    echo "Not supported on Python 3.2 due to issues with dependencies"
    exit 0
fi

pip install -e "git+https://github.com/pyca/cryptography#egg=cryptography"
cd ${VIRTUAL_ENV}/src/cryptography
python setup.py test
