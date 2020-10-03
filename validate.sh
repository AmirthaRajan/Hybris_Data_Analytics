#!/bin/sh

v_min="3.4.0"
v_max="3.7.0"
PYTHON_VERSION="$(python -c 'import platform; print(platform.python_version())')"

[ ! "$PYTHON_VERSION" = "$(echo -e "$PYTHON_VERSION\n$v_min\n$v_max" | sort -V | head -2 | tail -1)" ] && {
  echo "PHP Version $PYTHON_VERSION must be between $v_min - $v_max"
}

python python_script.py