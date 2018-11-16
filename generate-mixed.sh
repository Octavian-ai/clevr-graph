#!/bin/sh

python -m gqa.generate \
	--count 100000 \
	--small \
	--type-prefix StationProperty --type-prefix StationAdjacent --type-prefix StationShortestCount 