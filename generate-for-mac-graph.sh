#!/bin/sh

pipenv run "python -m gqa.generate --int-names --count 100000 --small --type-string-prefix StationProperty --type-string-prefix StationAdjacent"