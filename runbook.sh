#!/bin/bash

usage () {
  cat <<EOF
Usage: $0 [-s zellij_session_name] -f command_file [-f command_file ...] [-p] [-d]
  -s zellij_session_name    - Name of Zellij session where commands will be (optionally) executed
  -f command_file           - One or more command files in TOML format
  -p                        - Requires login password (from .streamlit/secrets.toml file)
  -d                        - Debug mode

EOF
  exit 1
}

command_files=()
use_password=0
debug=0

while getopts ":s:f:pd" opt; do
  case $opt in
    f)
      command_files+=("$OPTARG")  # Add the path to the paths array
      ;;
    s)
      session_name="$OPTARG"
      ;;
    p)
      use_password=1
      ;;
    d)
      debug=1
      ;;
    \?)
      echo "Invalid option: -$OPTARG" >&2
      usage
      ;;
    :)
      echo "Option -$OPTARG requires an argument." >&2
      usage
      ;;
  esac
done

if [ "${#command_files[@]}" -eq 0 ]; then
    echo "Error: At least one command file (-f command_file) is required."
    usage
fi

. venv/bin/activate
streamlit run \
  --client.toolbarMode viewer \
  --ui.hideTopBar true \
  --theme.base dark \
  runbook.py -- "$@"
