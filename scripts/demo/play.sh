#!/usr/bin/env bash
# Печатает команду «как будто набирает» и выполняет её (vhs плохо набирает кириллицу).
export PATH="${VENV_BIN:-.venv/bin}:$PATH"
type_run() {
  printf '\033[32m$\033[0m '
  local s="$1"; for ((i=0;i<${#s};i++)); do printf '%s' "${s:i:1}"; sleep 0.03; done; echo
  eval "$1"; echo; sleep "${2:-2}"
}
clear; sleep 0.5
printf '\033[90m# 577 BSL-файлов из открытых проектов Connector, YAxUnit, xUnitFor1C\033[0m\n'
type_run "find corpus -name '*.bsl' | wc -l" 1.2
type_run "code-search search corpus 'basic авторизация' --k 3" 3.5
type_run "code-search search corpus 'таймаут соединения' --k 3" 5
