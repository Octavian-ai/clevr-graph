
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
	def __init__(self, placeholders, english, functional, type_string, 
		type_id=None, 
		arguments_valid=(lambda *args:True), 
		answer_valid=(lambda *args:True) 
	):

		self.placeholders = placeholders
		self.english = english
		self.functional = functional
		self.type_id = type_id
		self.type_string = type_string
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
			logger.debug(f"Failed to generate cypher: {ex}")
			# traceback.print_exc()
			cypher = None

		if self.arguments_valid(graph, *raw_args) and self.answer_valid(graph, answer):
			return QuestionSpec(english, functional, cypher, self.type_id, self.type_string), answer

	


question_forms = [

	# --------------------------------------------------------------------------
	# Station properties
	# --------------------------------------------------------------------------

	QuestionForm(
		[Station], 
		"How clean is {}?", 
		(lambda s: Pick(s, "cleanliness")),
		"StationPropertyCleanliness"),

	QuestionForm(
		[Station], 
		"What is the cleanliness level of {} station?", 
		(lambda s: Pick(s, "cleanliness")),
		"StationPropertyCleanliness2"),

	QuestionForm(
		[Station], 
		"How big is {}?", 
		(lambda s: Pick(s, "size")),
		"StationPropertySize"),

	QuestionForm(
		[Station], 
		"What size is {}?", 
		(lambda s: Pick(s, "size")),
		"StationPropertySize2"),

	QuestionForm(
		[Station], 
		"What music plays at {}?", 
		(lambda s: Pick(s, "music")),
		"StationPropertyMusic"),

	QuestionForm(
		[Station], 
		"At {} what sort of music plays?", 
		(lambda s: Pick(s, "music")),
		"StationPropertyMusic2"),


	QuestionForm(
		[Station], 
		"What architectural style is {}?", 
		(lambda s: Pick(s, "architecture")),
		"StationPropertyArchitecture"),

	QuestionForm(
		[Station], 
		"Describe {} station's architectural style.", 
		(lambda s: Pick(s, "architecture")),
		"StationPropertyArchitecture2"),

	QuestionForm(
		[Station], 
		"Does {} have disabled access?", 
		(lambda s: Pick(s, "disabled_access")),
		"StationPropertyDisabledAccess"),

	QuestionForm(
		[Station], 
		"Is there disabled access at {}?", 
		(lambda s: Pick(s, "disabled_access")),
		"StationPropertyDisabledAccess2"),

	QuestionForm(
		[Station], 
		"Does {} have rail connections?", 
		(lambda s: Pick(s, "has_rail")),
		"StationPropertyHasRail"),

	
	QuestionForm(
		[Station], 
		"Can you get rail connections at {}?", 
		(lambda s: Pick(s, "has_rail")),
		"StationPropertyHasRail2"),

	# --------------------------------------------------------------------------
	
	QuestionForm(
		[Line], 
		"How many architectural styles does {} pass through?", 
		(lambda l: Count(Unique(Pluck(Nodes(Filter(AllEdges(), "line_id", Pick(l, "id"))),
								  "architecture"))) ),
		"LineTotalArchitectureCount"),

	QuestionForm(
		[Line], 
		"How many music styles does {} pass through?", 
		(lambda l: Count(Unique(Pluck(Nodes(Filter(AllEdges(), "line_id", Pick(l, "id"))),
								  "music"))) ),
		"LineTotalMusicCount"),

	QuestionForm(
		[Line], 
		"How many sizes of station does {} pass through?", 
		(lambda l: Count(Unique(Pluck(Nodes(Filter(AllEdges(), "line_id", Pick(l, "id"))),
								  "size"))) ),
		"LineTotalSizeCount"),

	# --------------------------------------------------------------------------

	QuestionForm(
		[Music, Line], 
		"How many stations playing {} does {} pass through?", 
		lambda v, l: CountIfEqual(
			Pluck(
				Nodes(Filter(AllEdges(), "line_id", Pick(l, "id"))),
				"music"
			),
			v
		),
		"LineFilterMusicCount"),

	QuestionForm(
		[Cleanliness, Line], 
		"How many {} stations does {} pass through?", 
		lambda v, l: CountIfEqual(
			Pluck(
				Nodes(Filter(AllEdges(), "line_id", Pick(l, "id"))),
				"cleanliness"
			),
			v
		),
		"LineFilterCleanlinessCount"),

	QuestionForm(
		[Size, Line], 
		"How many {} stations does {} pass through?", 
		lambda v, l: CountIfEqual(
			Pluck(
				Nodes(Filter(AllEdges(), "line_id", Pick(l, "id"))),
				"size"
			),
			v
		),
		"LineFilterSizeCount"),

	QuestionForm(
		[Line], 
		"How many stations with disabled access does {} pass through?", 
		lambda l: CountIfEqual(
			Pluck(
				Nodes(Filter(AllEdges(), "line_id", Pick(l, "id"))),
				"disabled_access"
			),
			True
		),
		"LineFilterDisabledAccessCount"),

	QuestionForm(
		[Line], 
		"How many stations with rail connections does {} pass through?", 
		lambda l: CountIfEqual(
			Pluck(
				Nodes(Filter(AllEdges(), "line_id", Pick(l, "id"))),
				"has_rail"
			),
			True
		),
		"LineFilterHasRailCount"),

	# --------------------------------------------------------------------------

	# Other way of expressing the How many program
	# QuestionForm(
	# 	[Architecture, Line], 
	# 	"How many {} stations are on the {} line?", 
	# 	(lambda a, l: Count(
	# 		Unique(Filter(
	# 			Nodes(Filter(AllEdges(), "line_id", Pick(l, "id"))),
	# 			"architecture",
	# 			a))
	# 	)),
	# 	"LineArchitectureCount"),


	
	# --------------------------------------------------------------------------

	QuestionForm(
		[Station, Station], 
		"How many stations are between {} and {}?", 
		(lambda a,b: Subtract(Count(ShortestPath(a, b, [])),2)),
		"StationShortestCount",
		arguments_valid=lambda g, a, b: a != b,
		answer_valid=lambda g, a: a >= 0),

	QuestionForm(
		[Station, Station], 
		"Are {} and {} adjacent?", 
		(lambda a,b: Equal(Count(ShortestPath(a, b, [])),2)),
		"StationAdjacent"),

	QuestionForm(
		[Architecture, Station], 
		"Which {} station is adjacent to {}?", 
		lambda a,b: UnpackUnitList(Pluck(Filter(Neighbors(b), "architecture", a), "name")),
		"StationArchitectureAdjacent"),

	QuestionForm(
		[Station, Station], 
		"Are {} and {} connected by the same station?", 
		(lambda a,b: Equal(Count(ShortestPath(a, b, [])),3)),
		"StationOneApart"),

	QuestionForm(
		[Station], 
		"Is there a station called {}?", 
		(lambda a: Const(True)),
		"StationExistence1"),

	QuestionForm(
		[FakeStationName], 
		"Is there a station called {}?", 
		(lambda a: Const(False)),
		"StationExistence2"),

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

	# Too often fails because it is ambiguous (multiple answers)
	# QuestionForm(
	# 	[Architecture, Cleanliness, Music],
	# 	"Which {} station is beside the {} station with {} music?",
	# 	lambda a, c, m: Pluck(First(UnpackUnitList(
	# 			FilterAdjacent(
	# 				Filter(AllNodes(), "architecture", a),
	# 				Filter(Filter(AllNodes(), "cleanliness", c), "music", m)
	# 			)
	# 		)
	# 		), "name"),
	# 	"NearestByProperties"
	# 	),



	# How to get from X to Y avoiding Z
]

for idx, form in enumerate(question_forms):
	form.type_id = idx









