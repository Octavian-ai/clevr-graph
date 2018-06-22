
import csv
import networkx as nx

from .types import *



class LondonGraph(object):

	def read(self):

		with open('./source_data/london.lines.csv', 'r') as file:
			r = csv.DictReader(file)
			lines = {}
			for i in r:
				lines[i["line"]] = Line(i)

		with open('./source_data/london.stations.csv', 'r') as file:
			r = csv.DictReader(file)
			nodes = {}
			for i in r:
				nodes[i["id"]] = Node(i)

		with open('./source_data/london.connections.csv', 'r') as file:
			r = csv.DictReader(file)
			edges = []
			for i in r:
				i["line_name"] = lines[i["line"]]["name"]
				edges.append(Edge(i))

		return GraphSpec(nodes, edges, lines)

def read():
	return LondonGraph().read()

if __name__ == "__main__":
	print(LondonGraph().read())

