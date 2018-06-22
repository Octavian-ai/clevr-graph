
import random
import networkx as nx
from collections import Counter
from inspect import signature

from .types import NodeSpec, EdgeSpec
from .generate_graph import EntityProperties

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
		"""Perform this individual operation"""
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

class Line(FunctionalOperator):
	@classmethod
	def get(self, graph):
		return Line(random.choice(list(graph.lines.values())))

class Architecture(FunctionalOperator):
	@classmethod
	def get(self, graph):
		return Architecture(random.choice(EntityProperties["architecture"]))

class Music(FunctionalOperator):
	@classmethod
	def get(self, graph):
		return Music(random.choice(EntityProperties["music"]))

class Cleanliness(FunctionalOperator):
	@classmethod
	def get(self, graph):
		return Cleanliness(random.choice(EntityProperties["cleanliness"]))

class Boolean(FunctionalOperator):
	@classmethod
	def get(self, graph):
		return Boolean(random.choice([True, False]))

# --------------------------------------------------------------------------
# General operations
# --------------------------------------------------------------------------


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
		return n


def ids_to_nodes(graph, ids):
	return [graph.nodes[i] for i in ids]

class ShortestPath(FunctionalOperator):
	def op(self, graph, a:NodeSpec, b:NodeSpec):
		return ids_to_nodes(graph, nx.shortest_path(graph.gnx, a["id"], b["id"]))

class Paths(FunctionalOperator):
	def op(self, graph, a:NodeSpec, b:NodeSpec):
		return [ids_to_nodes(graph, i) for i in nx.all_simple_paths(graph.gnx, a["id"], b["id"])]

class FilterAdjacent(FunctionalOperator): 
	def op(self, graph, a:List, b:List):
		r = []
		for i in a:
			for j in b:
				ns = graph.gnx.neighbors(i["id"])
				if j["id"] in ns:
					r.append([i,j])
		return r

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
		return Counter(l).most_common(1)[0][0]

class Unique(FunctionalOperator):
	def op(self, graph, l):
		return list(set(l))

class SlidingPairs(FunctionalOperator):
	def op(self, graph, l):
		return [(l[i], l[i+1]) for i in range(len(l)-1)]


@macro
def GetLines(a):
	return Unique(Pluck(Edges(a), "line_name"))

class HasIntersection(FunctionalOperator):
	def op(self, graph, a, b):
		for i in a:
			if i in b:
				return True
		return False

class Filter(FunctionalOperator):
	def op(self, graph, a:List, b, c):
		return [i for i in a if i[b] == c]

class UnpackUnitList(FunctionalOperator):
	"""This operator will raise if the given list is not length 1 - this is used as a guard against generating ambiguous questions"""
	def op(self, graph, l:List):
		if len(l) == 1:
			return l[0]
		else:
			raise ValueError(f"List is length {len(l)}, expected 1")

class First(FunctionalOperator):
	def op(self, graph, l:List):
		return l[0]

class MinBy(FunctionalOperator):
	def op(self, graph, a, b):
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





