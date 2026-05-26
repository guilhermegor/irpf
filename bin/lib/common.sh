#!/usr/bin/env bash
# Shared utilities for all bin/*.sh scripts — source, do not execute.

if [[ "${BASH_SOURCE[0]}" == "$0" ]]; then
    echo "bin/lib/common.sh is meant to be sourced, not executed." >&2
    exit 1
fi

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
MAGENTA='\033[0;35m'
NC='\033[0m'

print_status() {
    local status="$1"
    local message="$2"
    case "$status" in
        "success") echo -e "${GREEN}[✓]${NC} ${message}" ;;
        "error")   echo -e "${RED}[✗]${NC} ${message}" >&2 ;;
        "warning") echo -e "${YELLOW}[!]${NC} ${message}" ;;
        "info")    echo -e "${BLUE}[i]${NC} ${message}" ;;
        "config")  echo -e "${CYAN}[→]${NC} ${message}" ;;
        "debug")   echo -e "${MAGENTA}[»]${NC} ${message}" ;;
        *)         echo -e "[ ] ${message}" ;;
    esac
}

print_section() {
    echo -e "\n${MAGENTA}========================================${NC}"
    echo -e "${MAGENTA} ${1}${NC}"
    echo -e "${MAGENTA}========================================${NC}\n"
}
