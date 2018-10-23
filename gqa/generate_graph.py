
import uuid
import random
import numpy as np
import scipy
from sklearn.neighbors import KDTree
import networkx as nx
import bezier
import gibberish
import logging
from collections import OrderedDict, Counter
from tqdm import tqdm

logger = logging.getLogger(__name__)

from .types import GraphSpec, NodeSpec, EdgeSpec, LineSpec
from .args import *

LineProperties = {
	"has_aircon": [True, False],
	"color": ['blue', 'orange', 'green', 'red', 'purple', 'brown', 'pink', 'gray', 'olive', 'cyan'],
	"stroke": ["solid" , "dashed", "dashdot", "dotted"],
	"built": ["50s", "60s", "70s", "80s", "90s", "00s", "recent"],
}

StationProperties = {
	"disabled_access": [True, False],
	"has_rail": [True, False],
	"music": ["classical", "rock n roll", "rnb", "electronic", "country", "none", "swing", "pop"],
	"architecture": ["victorian", "modernist", "concrete", "glass", "art-deco", "new"],
	"size": ["tiny", "small", "medium-sized", "large", "massive"],
	"cleanliness": ["clean", 'dirty', 'shabby', 'derilict', 'rat-infested'],
}

OtherProperties = {
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

	def __init__(self, args):

		self.args = args

		self.stats = {
			"lines": 22,
			"stations_per_line": 20,
			"map_radius": 25,
			"min_station_dist": 0.8,
		}

		if args.tiny:
			self.stats["lines"] = 2
			self.stats["stations_per_line"] = 3
			self.stats["map_radius"] = 3
			# self.stats["min_station_dist"] = 1

		elif args.small:
			self.stats["lines"] = 5
			self.stats["stations_per_line"] = 5
			self.stats["map_radius"] = 5
			# self.stats["min_station_dist"] = 2


	def gen_a(self, Clz, prop_dict):
		return Clz({
			k : random.choice(prop_dict[k])
			for k in prop_dict.keys()
		})

	def gen_line(self):
		l = self.gen_a(GeneratedLine, LineProperties)
		name = l.p["color"] + " " + gibberish.generate_word()
		l.p["name"] = name.title()
		return l

	def gen_station(self):
		s = self.gen_a(GeneratedStation, StationProperties)
		name = gibberish.generate_word() + random.choice(OtherProperties["surname"])
		s.p["name"] = name.title()
		return s

	@property
	def station_set(self):
		line_stations_set = set()
		for line, stations in self.line_stations.items():
			line_stations_set.update(stations)
		return line_stations_set
	

	def gen_station_unique(self):
		for i in range(50):
			s = self.gen_station()
			
			if s not in self.station_gen_set:
				self.station_gen_set.add(s)
				return s

		raise Exception("Failed to generate unique station")

	def gen_lines(self):
		self.line_set = set()

		n = gen_n(self.stats["lines"])

		while len(self.line_set) < n:
			line = self.gen_line()
			self.line_set.add(line)


	def gen_stations(self):

		self.station_gen_set = set()
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

			if len(self.station_set) == 0:
				return frozenset()

			samples = []
			features = []

			for i in self.station_set:
				features.append(i)
				samples.append(i.pt)

			X = np.array(samples)
			tree = KDTree(X, 10)
			ind = tree.query_radius(X, self.stats["min_station_dist"])

			return frozenset([
				frozenset([ features[i] for i in group ]) for group in ind if len(group) > 1
			])


		def repif(cur, tar, rep):
			if cur == tar:
				return rep
			else:
				return cur

		def remove_dupes(l):
			return list(OrderedDict.fromkeys(l))

		def replace_station(target, replacement):
			self.line_stations = {
				line: remove_dupes([repif(i, target, replacement) for i in stations])
				for line, stations in self.line_stations.items()
			}
			
		# Coalesce nearby stations on lines
		# Coalesce stations between lines
		logger.debug("Coalesce stations")
		for i in range(30):
			groups = find_nearby_stations()

			if len(groups) == 0:
				break

			logger.debug(f"Found {len(groups)} groups of nearby stations")
			for a, *rest in groups:
				for b in rest:
					replace_station(b, a)


	def gen_int_names(self):
		for sett in [self.line_set, self.station_set]:
			int_names = list(range(len(sett) * 2)) # allocate more names than stations so we can test for existence
			random.shuffle(int_names)
			for i, item in enumerate(sett):
				item.p["name"] = str(int_names[i])
		
		

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
						"station1_name": i.p["name"],
						"station2": stations[idx+1].p["id"],
						"station2_name": stations[idx+1].p["name"],
					}

					b = line.to_attr_dict()

					edges.append(EdgeSpec({**a, **b}))


		self.graph_spec = GraphSpec(
			nodes, edges, lines
		)

	def assert_data_valid(self):
		if self.args.int_names:
			for stations in self.line_stations.values():
				for s in stations:
					int(s.p["name"])


	def generate(self):

		self.gen_lines()
		logger.debug("Generated lines")
		self.gen_stations()

		if self.args.int_names:
			self.gen_int_names()
			logger.debug("Generated int names")

		self.gen_graph_spec()

		self.assert_data_valid()

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
			ax.plot(inter_xs, inter_ys, color='grey', marker='s', ls='', markersize=10)

			for i in stations:
				ax.annotate(i.p["name"], i.pt)



		with open(filename, 'wb') as file:
			plt.savefig(file) 


if __name__ == "__main__":

	args = get_args()

	logger.setLevel('DEBUG')
	logging.basicConfig()

	import matplotlib
	matplotlib.use("Agg") # Work in terminal
	from matplotlib import pyplot as plt

	g = GraphGenerator(args)
	g.generate()
	g.draw()
	


