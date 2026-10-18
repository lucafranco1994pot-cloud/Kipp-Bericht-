#!/usr/bin/env bash
# Verschiebt das gerade erzeugte Backtest-Ergebnis (wo immer Freqtrade es abgelegt hat) in den Ordner $1.
set -e
mkdir -p "$1"
find . -name 'backtest-result-*' -not -path './erg_*/*' -print -exec mv {} "$1"/ \;
