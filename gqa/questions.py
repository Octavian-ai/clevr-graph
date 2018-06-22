
import logging
logger = logging.getLogger(__name__)

import traceback

from .functional import *
from .types import QuestionSpec
from networkx.exception import NetworkXNoPath

from gql import GqlBuilder

# --------------------------------------------------------------------------
# Directory of question types
# --------------------------------------------------------------------------



class QuestionForm(object):
	def __init__(self, placeholders, english, functional, tpe, arguments_valid=lambda *args:True, answer_valid=lambda *args:True):
		self.placeholders = placeholders
		self.english = english
		self.functional = functional
		self.tpe = tpe
		self.arguments_valid = arguments_valid
		self.answer_valid = answer_valid

	def __repr__(self):
		return self.english

	def english_explain(self):
		return self.english.format(
			*[f"{{{i.__name__}}}" for i in self.placeholders]
		)

	def generate(self, graph):		
		args = [i.get(graph) for i in self.placeholders]
		raw_args = [i.args[0] for i in args]

		def englishify(s):
			try:
				return s.name()
			except AttributeError:
				return s

		english_args = [englishify(i) for i in raw_args]

		english = self.english.format(*english_args)
		answer = self.functional(*raw_args)(graph)
		functional = self.functional(*args).stripped()

		try:
			cypher = GqlBuilder(functional).build()
		except Exception as ex:
			logger.warning(f"Failed to generate cypher: {ex}")
			# traceback.print_exc()
			cypher = None

		if self.arguments_valid(graph, *raw_args) and self.answer_valid(graph, answer):
			return QuestionSpec(english, functional, cypher, self.tpe), answer

	


question_forms = [

	QuestionForm(
		[Station, Station], 
		"How many stations are between {} and {}?", 
		(lambda a,b: Subtract(Count(ShortestPath(a, b)),2)),
		"StationShortestCount",
		arguments_valid=lambda g, a, b: a != b,
		answer_valid=lambda g, a: a >= 0),

	QuestionForm(
		[Station], 
		"Which lines is {} on?", 
		(lambda a: GetLines(a)),
		"StationLine"),

	QuestionForm(
		[Station], 
		"How many lines is {} on?", 
		(lambda a: Count(GetLines(a))),
		"StationLineCount"),

	QuestionForm(
		[Station], 
		"How clean is {}?", 
		(lambda a: Pick(a, "cleanliness")),
		"StationCleanliness"),

	QuestionForm(
		[Station, Station], 
		"Are {} and {} on the same line?", 
		(lambda a, b: HasIntersection(GetLines(a), GetLines(b)) ),
		"StationSameLine",
		arguments_valid=lambda g, a, b: a != b),

	QuestionForm(
		[Line], 
		"Which stations does {} pass through?", 
		(lambda a: Pluck(Unique(Nodes(Filter(AllEdges(), "line_id", Pick(a, "id")))), "name")),
		"LineStations"),

	QuestionForm(
		[Line], 
		"How many architecture styles does {} pass through?", 
		(lambda a: Count(Unique(Pluck(Nodes(Filter(AllEdges(), "line_id", Pick(a, "id"))), "architecture"))) ),
		"LineTotalArchitectureCount"),

	QuestionForm(
		[Architecture, Line], 
		"How many {} stations are on the {} line?", 
		(lambda a, l: CountIfEqual((Pluck(Nodes(Filter(AllEdges(), "line_id", Pick(l, "id"))), "architecture")), a) ),
		"LineArchitectureCount"),

	QuestionForm(
		[Architecture],
		"Which line has the most {} stations?",
		(lambda a: Mode(Pluck(Edges(Filter(AllNodes(), "architecture", a)), "line_name")) ),
		"LineMostArchitecture"),

	# Too slow, needs better impl (e.g. construct meta-graph of interchanges)
	# QuestionForm(
	# 	[Station, Station],
	# 	"What route has the fewest changes between {} and {}?",
	# 	lambda a, b: Pluck(
	# 		MinBy(
	# 			Paths(a, b), 
	# 			lambda x: Count(Unique(SlidingPairs(GetLines(x))))
	# 		), "name"),
	# 	"LineMostArchitecture"),

	QuestionForm(
		[Station],
		"What's the nearest station to {} with disabled access?",
		lambda x: Pick(MinBy(
			FilterHasPathTo(Filter(AllNodes(), "disabled_access", True), x), 
			lambda y: Count(ShortestPath(x, y))
		), "name"),
		"NearestStationDisabledAccess"),

	QuestionForm(
		[Architecture, Cleanliness, Music],
		"Which {} station is beside the {} station with {} music?",
		lambda a, c, m: Pluck(First(UnpackUnitList(
				FilterAdjacent(
					Filter(AllNodes(), "architecture", a), 
					Filter(Filter(AllNodes(), "cleanliness", c), "music", m)))
			), "name"),
		"NearestByProperties"
		),



	# How to get from X to Y avoiding Z
]









