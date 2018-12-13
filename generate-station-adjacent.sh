#!/bin/bash

tenth=100
j=StationAdjacent

for i in `seq 1 10`
do
	nohup python -m gqa.generate \
		--count $tenth \
		--small \
		--type-prefix $j \
		--name $j-$i &
done