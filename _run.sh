#!/usr/bin/env bash

for yymm in 090{1..9} 09{10..12}; do
    python a2_dwellTimeNpriorPresence.py $yymm &
done