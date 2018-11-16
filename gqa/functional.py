
import random
import networkx as nx
from collections import Counter
from inspect import signature

from .types import NodeSpec, EdgeSpec
from .generate_graph import StationProperties, LineProperties

from typing import List, Dict

import logging
logger = logging.getLogger(__name__)

# --------------------------------------------------------------------------
# Executable syntax tree to represent and calculate answers
# --------------------------------------------------------------------------

class FunctionalOperator(object):
	def __init__(self, *args):
		self.args = args

	def __call__(self, graph):
		"""Execute this whole program to get an answer"""

		def ex(item):
			if isinstance(item, FunctionalOperator):
				return item(graph)
			else:
				return item

		vals = [ex(i) for i in self.args]
		try:
			return self.op(graph, *vals)
		except Exception as ex:
			logger.debug("Failed to execute operation {}({}) {}".format(type(self).__name__, vals, ex))
			raise ex

	def op(self, *args):
		"""
		Perform this individual operation

		Operations should raise ValueError if it is not possible to generate
		a valid answer, but no error has occured. This exception will be silently
		swallowed.

		"""
		raise NotImplementedError()

	def stripped(self):
		"""Represent this program for export"""

		def ex(item):
			try:
				return item.stripped()
			except AttributeError:

				# YAML export will freak out if it hits a lambda, so symbolically replace it
				if callable(item):
					sig = signature(item)
					args = [LambdaArg(i) for i in sig.parameters]
					return Lambda(item(*args)).stripped()
				else:
					return item

		k = [ex(i) for i in self.args]
		
		r = {}
		r[type(self).__name__] = k
		return r

def macro(f):
	return f


# --------------------------------------------------------------------------
#  Noun operations
# --------------------------------------------------------------------------

class Station(FunctionalOperator):
	@classmethod
	def get(self, graph):
		return Station(random.choice(list(graph.nodes.values())))

class FakeStationName(FunctionalOperator):
	@classmethod
	def get(self, graph):
		# This needs generalised later
		actual_station_names = {str(j.name()) for j in graph.nodes.values()}
		max_stn = len(graph.nodes) * 2
		nonexistent_stations = [i for i in range(max_stn) if str(i) not in actual_station_names]
		return FakeStationName(random.choice(nonexistent_stations))

class StationPropertyName(FunctionalOperator):
	@classmethod
	def get(self, graph):
		return StationPropertyName(random.choice(StationProperties.keys()))

class StationProperty(FunctionalOperator):
	@classmethod
	def get(self, graph):
		key = random.choice(list(StationProperties.keys()))
		return StationProperty(key, StationProperties[key])

class Line(FunctionalOperator):
	@classmethod
	def get(self, graph):
		return Line(random.choice(list(graph.lines.values())))

class Architecture(FunctionalOperator):
	@classmethod
	def get(self, graph):
		return Architecture(random.choice(StationProperties["architecture"]))

class Size(FunctionalOperator):
	@classmethod
	def get(self, graph):
		return Size(random.choice(StationProperties["size"]))

class Music(FunctionalOperator):
	@classmethod
	def get(self, graph):
		return Music(random.choice(StationProperties["music"]))

class Cleanliness(FunctionalOperator):
	@classmethod
	def get(self, graph):
		return Cleanliness(random.choice(StationProperties["cleanliness"]))

class Boolean(FunctionalOperator):
	@classmethod
	def get(self, graph):
		return Boolean(random.choice([True, False]))

# --------------------------------------------------------------------------
# General operations
# --------------------------------------------------------------------------

class Const(FunctionalOperator):
	def op(self, graph, a):
		return a

class Lambda(FunctionalOperator):
	def op(self, graph, a):
		return a

class LambdaArg(FunctionalOperator):
	def op(self, graph, a):
		return a

class Pluck(FunctionalOperator):
	def op(self, graph, a, b):
		return [i[b] for i in a]

class Pick(FunctionalOperator):
	def op(self, graph, a, b):
		return a[b]

class Equal(FunctionalOperator):
	def op(self, graph, a, b):
		return a == b



# --------------------------------------------------------------------------
# Graph operations
# --------------------------------------------------------------------------

class AllEdges(FunctionalOperator):
	def op(self, graph):
		return graph.edges

class AllNodes(FunctionalOperator):
	def op(self, graph):
		return graph.nodes.values()

class Edges(FunctionalOperator):
	def op(self, graph, a):
		if isinstance(a, NodeSpec):
			return [edge[2]['attr_dict'] for edge in graph.gnx.edges([a["id"]], data=True)]
		else:
			return [
				edge[2]['attr_dict'] 
				for node in a
				for edge in graph.gnx.edges([node["id"]], data=True) 
			]

class Nodes(FunctionalOperator):
	def op(self, graph, edges:EdgeSpec):
		n = []
		for i in edges:
			n.append(graph.nodes[i["station1"]])
			n.append(graph.nodes[i["station2"]])
		return list(set(n))


def ids_to_nodes(graph, ids):
	return [graph.nodes[i] for i in ids]

class ShortestPath(FunctionalOperator):
	def op(self, graph, a:NodeSpec, b:NodeSpec, fallback):
		try:
			return ids_to_nodes(graph, nx.shortest_path(graph.gnx, a["id"], b["id"]))
		except nx.exception.NetworkXNoPath:
			return fallback

class ShortestPathOnlyUsing(FunctionalOperator):
	def op(self, graph, a:NodeSpec, b:NodeSpec, only_using_nodes:List[NodeSpec], fallback):
		try:
			induced_subgraph = nx.induced_subgraph(graph.gnx, [i["id"] for i in only_using_nodes + [a,b]])
			return ids_to_nodes(graph, nx.shortest_path(induced_subgraph, a["id"], b["id"]))
		except nx.exception.NetworkXNoPath:
			return fallback

class Paths(FunctionalOperator):
	def op(self, graph, a:NodeSpec, b:NodeSpec):
		return [ids_to_nodes(graph, i) for i in nx.all_simple_paths(graph.gnx, a["id"], b["id"])]


class HasCycle(FunctionalOperator):
	def op(self, graph, a:NodeSpec):

		# Would all_simple_paths also solve this for us?

		def canonical_edge(e):
			return (frozenset(e[:2]), e[2]["attr_dict"]["line_id"])

		def dfs_unidirected_cycle(head_id, path_nodes=frozenset(), path_edges=frozenset(), indent=""):
			for e in graph.gnx.edges([head_id], data=True):
				assert e[0] == head_id
				assert head_id in path_nodes

				from_id = head_id
				to_id = e[1]

				# Nothing new
				if canonical_edge(e) in path_edges:
					continue

				# If we've returned home
				if to_id == a["id"]:
					return True

				# Nothing new
				if to_id in path_nodes:
					continue
			
				ir = dfs_unidirected_cycle(
					to_id, 
					path_nodes | set([to_id]), 
					path_edges | set([canonical_edge(e)]),
					indent=indent+"  ",
				)

				if ir:
					return True


			return False
		return dfs_unidirected_cycle(a["id"], frozenset([a["id"]]))

class FilterAdjacent(FunctionalOperator): 
	def op(self, graph, a:List, b:List):
		r = []
		for i in a:
			for j in b:
				ns = graph.gnx.neighbors(i["id"])
				if j["id"] in ns:
					r.append([i,j])
		return r

class Neighbors(FunctionalOperator):
	def op(self, graph, station:NodeSpec):
		return ids_to_nodes(graph, graph.gnx.neighbors(station["id"]))

class WithinHops(FunctionalOperator):
	def op(self, graph, station:NodeSpec, hops:int):
		rs = set()
		tips = set([station])
		for i in range(hops):
			next_tips = set()
			for j in tips:
				next_tips |= set(ids_to_nodes(graph, graph.gnx.neighbors(j["id"])))

			rs |= tips
			tips = next_tips - rs

		rs |= next_tips
		rs.remove(station)
		return list(rs)





class FilterHasPathTo(FunctionalOperator):
	def op(self, graph, a:List, b:NodeSpec):
		return [i for i in a if nx.has_path(graph.gnx, i["id"], b["id"])]


# --------------------------------------------------------------------------
# List operators
# --------------------------------------------------------------------------

class NotEmpty(FunctionalOperator):
	def op(self, graph, l):
		return len(l) > 0

class Count(FunctionalOperator):
	def op(self, graph, l):
		return len(l)

class CountIfEqual(FunctionalOperator):
	def op(self, graph, l, t):
		return len([i for i in l if i == t])

class Mode(FunctionalOperator):
	def op(self, graph, l):

		if len(l) == 0:
			raise ValueError("Cannot find mode of empty sequence")

		c = Counter(l)
		most = c.most_common(2)

		# Only one unique value in l
		if len(most) == 1:
			return most[0][0]

		# If the most common occurs more than any other
		if most[0][1] > most[1][1]:
			return most[0][0]

		raise ValueError("No unique mode")

class Unique(FunctionalOperator):
	def op(self, graph, l):
		return list(set(l))

class SlidingPairs(FunctionalOperator):
	def op(self, graph, l):
		return [(l[i], l[i+1]) for i in range(len(l)-1)]


@macro
def GetLines(a):
	return Unique(Pluck(Edges(a), "line_name"))

@macro
def Adjacent(a, b):
	return Equal(Count(ShortestPath(a, b, [])), 2)

@macro
def CountNodesBetween(a):
	return Subtract(Count(a), 2)

class HasIntersection(FunctionalOperator):
	def op(self, graph, a, b):
		for i in a:
			if i in b:
				return True
		return False

class Intersection(FunctionalOperator):
	def op(self, graph, a, b):
		return list(set(a) & set(b))

class Filter(FunctionalOperator):
	def op(self, graph, a:List, b, c):
		return [i for i in a if i[b] == c]

class Without(FunctionalOperator):
	def op(self, graph, a:List, b, c):
		return [i for i in a if i[b] != c]

class UnpackUnitList(FunctionalOperator):
	"""This operator will raise if the given list is not length 1 - this is used as a guard against generating ambiguous questions"""
	def op(self, graph, l:List):
		if len(l) == 1:
			return l[0]
		else:
			raise ValueError(f"List is length {len(l)}, expected 1")

class Sample(FunctionalOperator):
	def op(self, graph, l:List, n:int):
		if len(l) < n:
			raise ValueError(f"Cannot sample {n} items from list of length {len(l)}")
		else:
			return random.choices(l, k=n)

class First(FunctionalOperator):
	def op(self, graph, l:List):
		return l[0]

class MinBy(FunctionalOperator):
	def op(self, graph, a, b):
		if len(a) == 0:
			raise ValueError("Cannot perform MinBy on empty list")
		return min(a, key=lambda i: b(i)(graph))


# --------------------------------------------------------------------------
# Numerical operations
# --------------------------------------------------------------------------


class Subtract(FunctionalOperator):
	def op(self, graph, a, b):
		return a - b


class Round(FunctionalOperator):
	def op(self, graph, a):
		try:
			return [round(float(i)) for i in a]
		except TypeError:
			return round(float(a))





