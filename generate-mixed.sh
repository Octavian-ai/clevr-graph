#!/bin/sh

python -m gqa.generate \
	--count 100000 \
	--small \
	--disable-cypher \
	--type-prefix StationProperty --type-prefix StationAdjacent --type-prefix StationShortestCount 