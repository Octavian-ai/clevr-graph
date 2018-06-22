
import uuid
import random
import numpy as np
import scipy
import networkx as nx
import bezier
import gibberish
import logging
from collections import OrderedDict, Counter
from tqdm import tqdm

logger = logging.getLogger(__name__)

from .types import GraphSpec, NodeSpec, EdgeSpec, LineSpec

EntityProperties = {
	"color": ['blue', 'orange', 'green', 'red', 'purple', 'brown', 'pink', 'gray', 'olive', 'cyan'],
	"stroke": ["solid" , "dashed", "dashdot", "dotted"],
	"built": ["50s", "60s", "70s", "80s", "90s", "00s", "recent"],
	"has_aircon": [True, False],
	"disabled_access": [True, False],
	"has_rail": [True, False],
	"music": ["classical", "rock n roll", "rnb", "electronic", "country", "none", "swing", "pop"],
	"architecture": ["victorian", "modernist", "concrete", "glass", "art-deco", "new"],
	"size": ["tiny", "small", "medium", "large", "massive"],
	"cleanliness": ["clean", 'dirty', 'shabby', 'derilict', 'rat-infested'],
	"surname": [" street", " st", " road", " court", " grove", "bridge", " bridge", " lane", " way", " boulevard", " crossing", " square", "ham", ' on trent', ' upon Thames', ' international', ' hospital', 'neyland', 'ington', 'ton', 'wich', ' manor', ' estate', ' palace']
}

class GeneratedEntity(object):
	def __init__(self, properties):
		self.p = properties
		self.p["id"] = str(uuid.uuid4())

	def __hash__(self):
		h = [self.p[i] for i in type(self).hash_properties]
		return hash(frozenset(h))

	def __repr__(self):
		return str(self.p)


class GeneratedStation(GeneratedEntity):
	hash_properties = ["name"]

	@property
	def pt(self):
		return [self.p["x"], self.p["y"]]

	def dist(self, other):
		return scipy.spatial.distance.euclidean(self.pt, other.pt)

	def __repr__(self):
		return self.p["name"]
	
class GeneratedLine(GeneratedEntity):
	hash_properties = ["color", "stroke"]

	def to_attr_dict(self):
		return {
			"line_id":    self.p["id"],
			"line_name":  self.p["name"],
			"line_color": self.p["color"],
			"line_stroke": self.p["stroke"],
		}


def gen_n(base, noise = 0.3):
	return round(random.gauss(base, noise*base))

def add_noise(base, noise=0.05):
	return base * (1 - noise + random.random() * noise*2)


class GraphGenerator(object):

	def __init__(self, small=False):

		self.stats = {
			"lines": 22,
			"stations_per_line": 20,
			"map_radius": 25,
			"min_station_dist": 0.8,
		}

		if small:
			self.stats["lines"] = 2
			self.stats["stations_per_line"] = 3


	def gen_a(self, Clz, *props):
		return Clz({
			i : random.choice(EntityProperties[i])
			for i in props
		})

	def gen_line(self):
		l = self.gen_a(GeneratedLine, "color", "stroke", "built", "has_aircon")
		name = l.p["color"] + " " + gibberish.generate_word()
		l.p["name"] = name.title()
		return l

	def gen_station(self):
		s = self.gen_a(GeneratedStation, "disabled_access", "has_rail", "music", "architecture", "size", "cleanliness")
		name = gibberish.generate_word() + random.choice(EntityProperties["surname"])
		s.p["name"] = name.title()
		return s

	def gen_station_unique(self):
		while True:
			s = self.gen_station()
			if s not in self.station_set:
				self.station_set.add(s)
				return s

	def gen_lines(self):
		self.line_set = set()

		n = gen_n(self.stats["lines"])

		while len(self.line_set) < n:
			self.line_set.add(self.gen_line())


	def gen_stations(self):

		self.station_set = set()
		self.line_stations = {}
		
		for line in self.line_set:

			xs = []
			ys = []
			
			for i in range(4):
				x = (random.random()*2-1) * self.stats["map_radius"]
				y = (random.random()*2-1) * self.stats["map_radius"]
				xs.append(x)
				ys.append(y)

			curve = bezier.curve.Curve.from_nodes(np.array([xs,ys]))

			# z = np.polyfit(xs, ys, 3)
			# p = np.poly1d(z)

			pts = curve.evaluate_multi(np.linspace(0,1, max(2, gen_n(self.stats["stations_per_line"]))))

			# xp = np.linspace(xs[0], xs[-1], gen_n(self.stats["stations_per_line"]))
			# yp = p(xp)

			stations = []

			# for x, y in zip(xp, yp):
			for [x,y] in np.transpose(pts):
				s = self.gen_station_unique()
				s.p["x"] = float(add_noise(x))
				s.p["y"] = float(add_noise(y))
				
				stations.append(s)

			self.line_stations[line] = stations
		
		# Helpers for coalesce operation

		def find_nearby_stations():
			# If you want to make this faster first sort all the stations into quadrants
			pairs = []

			# all_stations = set()
			# for line, stations in self.line_stations.items():
			# 	for id_i, i in enumerate(stations):
			# 		all_stations.add(i)

			# pts = [i.pt for i in all_stations]
			# tree = scipy.spatial.KDTree(pts, self.stats["min_station_dist"]*4)
			# return tree.query_pairs(self.stats["min_station_dist"])

			for line, stations in self.line_stations.items():
				for id_i, i in enumerate(stations):
					for other_line, other_stations in self.line_stations.items():
						for id_j, j in enumerate(other_stations):
							if i != j and i.dist(j) < self.stats["min_station_dist"]:
								if (j, i) not in pairs:
									pairs.append((i, j))

			if len(pairs) > 0:
				return pairs

			raise StopIteration()

		def repif(cur, tar, rep):
			if cur == tar:
				return rep
			else:
				return cur

		def remove_dupes(l):
			return list(OrderedDict.fromkeys(l))

		def replace_station(target, replacement):
			# logger.info("Replace station {} with {}".format(b, a))
			self.line_stations = {
				line: remove_dupes([repif(i, target, replacement) for i in stations])
				for line, stations in self.line_stations.items()
			}

		# Coalesce nearby stations on lines
		# Coalesce stations between lines
		try:
			logger.debug("Coalesce stations")
			for i in range(30):
				pairs = find_nearby_stations()
				for a, b in pairs:
					replace_station(b, a)

		except StopIteration:
			pass


	def gen_graph_spec(self):
		
		nodes = {}
		edges = []
		lines = {}

		for line in self.line_set:
			lines[line.p["id"]] = LineSpec(line.p)

		for line, stations in self.line_stations.items():
			for idx, i in enumerate(stations):
				nodes[i.p["id"]] = NodeSpec(i.p)

				if idx+1 < len(stations):

					a = {
						"station1": i.p["id"],
						"station2": stations[idx+1].p["id"],
					}

					b = line.to_attr_dict()

					edges.append(EdgeSpec({**a, **b}))


		self.graph_spec = GraphSpec(
			nodes, edges, lines
		)


	def generate(self):

		self.gen_lines()
		logger.debug("Generated lines")
		self.gen_stations()
		self.gen_graph_spec()

		# For chaining
		return self

	
	

	def draw(self, filename="./graph.png"):

		fig, ax = plt.subplots(figsize=(30, 30))

		lines_per_station = Counter()
		for line, stations in self.line_stations.items():
			for station in stations:
				lines_per_station[station] += 1


		for line, stations in self.line_stations.items():
			xs = [i.p["x"] for i in stations]
			ys = [i.p["y"] for i in stations]
			ts = [i.p["name"] for i in stations]
			ls = line.p["stroke"]
			c = 'tab:'+line.p["color"]
			ax.plot(xs, ys, color=c, marker='.', ls=ls, lw=4, markersize=16)

			inter_xs = [i.p["x"] for i in stations if lines_per_station[i] > 1]
			inter_ys = [i.p["y"] for i in stations if lines_per_station[i] > 1]
			ax.plot(inter_xs, inter_ys, color='grey', marker='.', ls='', markersize=16)

			for i in stations:
				ax.annotate(i.p["name"], i.pt)



		with open(filename, 'wb') as file:
			plt.savefig(file) 


if __name__ == "__main__":

	logger.setLevel('DEBUG')
	logging.basicConfig()

	import matplotlib
	matplotlib.use("Agg") # Work in terminal
	from matplotlib import pyplot as plt

	g = GraphGenerator()
	g.generate()
	g.draw()
	


