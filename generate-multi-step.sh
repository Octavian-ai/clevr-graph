#!/bin/bash

for i in `seq 1 10`
do
	for j in StationShortestCount StationShortestAvoidingCount StationTwoHops NearestStationArchitecture DistinctRoutes CountCycles
	do
		nohup python -m gqa.generate \
			--count 100 \
			--small \
			--type-prefix $j \
			--name $j-$i &

	done
done