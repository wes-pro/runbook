#!/bin/bash

if [[ $# -ne 2 ]]; then
    echo "Provide zellij layout name as first parameter and session name as second"
    exit 1
fi

zellij -l "$1" attach --create "$2" -f
