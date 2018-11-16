
from typing import Dict, Tuple, List, Any
import uuid
import networkx as nx

# --------------------------------------------------------------------------
# Data types for export to YAML
# --------------------------------------------------------------------------


class Strippable(object):

	def stripped(self):
		state = self.__getstate__()
		def tryStrip(i):
			try:
				return i.stripped()
			except AttributeError:
				try:
					return [j.stripped() for j in i]
				except Exception:
					return i

		return {
			k: tryStrip(v) for k, v in state.items()
		}


class QuestionSpec(Strippable):
	def __init__(self, english, functional, cypher, type_id, type_string, group):
		self.english = english
		self.functional = functional
		self.cypher = cypher
		self.type_id = type_id
		self.type_string = type_string
		self.group = group
		
		

	def __repr__(self):
		return self.english

	def __getstate__(self):
		return {
			"english": self.english,
			"functional": self.functional,
			"type_string": self.type_string,
			"type_id": self.type_id,
			"cypher": self.cypher,
			"group": self.group,
			"type": {
				"id": self.type_id,
				"name": self.type_string,
			}
		}


class YAMLExportDict(Strippable):
	def __init__(self, state={}):
		self.state = state

	def __getitem__(self, key):
		return self.state[key]

	def __setitem__(self, key, value):
		self.state[key] = value

	def __getstate__(self):
		return self.state

	def __setstate__(self, state):
		self.state = state

	def __repr__(self):
		return str(self.state)

class NodeSpec(YAMLExportDict):

	def name(self):
		return self.state["name"]

	def __hash__(self):
		return hash(self.state["id"])


class EdgeSpec(YAMLExportDict):
	pass

class LineSpec(YAMLExportDict):

	def name(self):
		return self.state["name"]

	def __hash__(self):
		return hash(self["id"])

class GraphSpec(Strippable):

	def __init__(self, nodes:Dict[str, NodeSpec], edges:List[EdgeSpec], lines:Dict[str, LineSpec]):
		self.id = str(uuid.uuid4())
		self.nodes = nodes
		self.edges = edges
		self.lines = lines
		self.gen_gnx()

	def gen_gnx(self):
		self.gnx = nx.Graph()
		
		for i in self.nodes.values():
			self.gnx.add_node(i["id"], attr_dict=i)

		for i in self.edges:
			self.gnx.add_edge(i["station1"], i["station2"], attr_dict=i)

	def __getstate__(self):
		return {
			"id": self.id,
			"nodes": list(self.nodes.values()),
			"edges": self.edges,
			"lines": list(self.lines.values()),
		}

	def __setstate__(self, state):
		self.id = state["id"]
		self.edges = state["edges"]
		# print([i.__dict__ for i in state["nodes"]])
		self.nodes = {i["id"]:i for i in state["nodes"]}
		self.lines = {i["id"]:i for i in state["lines"]}
		self.gen_gnx()


class DocumentSpec(Strippable):
	def __init__(self, graph:GraphSpec, question:QuestionSpec, answer:Any):
		self.graph = graph
		self.question = question
		self.answer = answer

	def __getstate__(self):
		return {
			"graph": self.graph,
			"question": self.question,
			"answer": self.answer
		}


