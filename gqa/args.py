
import argparse

def get_args():
	parser = argparse.ArgumentParser()
	parser.add_argument('--group', type=str, default=None)
	parser.add_argument('--type-prefix', action="append", help="Only generate questions of type prefix")

	parser.add_argument('--name', type=str, default=None)

	parser.add_argument('--count', type=int, default=1000, help="Number of (G,Q,A) to generate in thousands")
	parser.add_argument('--just-one', action='store_true')

	parser.add_argument('--log-level', type=str, default='INFO')
	parser.add_argument('--questions-per-graph', type=int, default=1, help="Number of (Q,A) per G")
	parser.add_argument('--omit-graph', action='store_true', help="Don't export the graph")
	parser.add_argument('--string-names', action='store_false', dest="int_names", help="Use integers as names")
	parser.add_argument('--enable-cypher', action='store_true', dest='generate_cypher')
	parser.add_argument('--draw', action='store_true', help="Write image of graphs")

	parser.add_argument('--tiny',  action='store_true', help="Generate really small graphs (faster)")
	parser.add_argument('--small', action='store_true', help="Generate small graphs (faster)")
	
	return parser.parse_args()