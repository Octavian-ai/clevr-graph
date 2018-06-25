from typing import Dict, Any, List, AnyStr
from .graph_builder import cypherencode, cypherparse, quote
from gqa.types import NodeSpec, EdgeSpec, LineSpec
import copy

class Var(object):
    def __init__(self, val: str):
        self.val = val

    def __str__(self):
        return self.val

def unquote(var: str):
    return str(var).replace('"','')


"""
MATCH (var1)
WHERE var1.name="South Harrow"
WITH var1
MATCH (var2)
WHERE var2.name="Greenford"
WITH var1,var2
MATCH var3 = shortestPath((var1)-[*]-(var2))
WITH var1,var2, var3, length(var3) as var4
WITH var1,var2, var3, var4, var4-2 as var5
RETURN var5
"""

class CypherState(object):
    def __init__(self, value: int):
        self.val = value

    def __lt__(self, other):
        return self.val < other.val

    def __gt__(self, other):
        return self.val > other.val

    def __eq__(self, other):
        return self.val == other.val



MATCH = CypherState(1)
WITH = CypherState(2)
RETURN = CypherState(3)


class GqlBuilder(object):
    def __init__(self, fp: Dict[str, Any]):
        super(GqlBuilder, self).__init__()
        self._stack = []
        self.fp = copy.deepcopy(fp)
        self.ops = {
            "Subtract": self.subtract,
            "Count": self.count,
            "ShortestPath": self.shortest_path,
            "Station": self.station,
            "Line": self.line,
            "Architecture": self.architecture,
            "Boolean": self.boolean,
            "Unique": self.unique,
            "Pluck": self.pluck,
            "Pick": self.pick,
            "Edges": self.edges,
            "Nodes": self.nodes,
            "AllEdges": self.allEdges,
            "Filter": self.filter,
        }
        self.current_var = 0
        self.current_tmp = 0
        self.current_where = []
        self.current_state = MATCH
        self.specials = []

    def allEdges(self):
        if self.current_state > MATCH:
            raise NotImplementedError()

        var = self.get_var()
        subquery = f"MATCH ()-[{var}]-()) "
        self._stack.append(subquery)
        return var

    def nodes(self, a: Var):
        vars = self.get_simple_with()
        tmp = self.get_tmp()
        if self.current_state == MATCH:
            self._do_where_clause()
        if self.current_state == WITH:
            self.do_with_to_match_transition()
        self._stack.append(f"MATCH ({tmp})-[{a}]-()")
        var2 = self.get_var()
        self._stack.append(f"WITH {vars}, collect({tmp}) AS {var2}")
        return var2

    def edges(self, a: Var):
        vars = self.get_simple_with()
        tmp = self.get_tmp()
        if self.current_state == MATCH:
            self._do_where_clause()
        if self.current_state == WITH:
            self.do_with_to_match_transition()
        self._stack.append(f"MATCH ({a})-[{tmp}]-()")
        var2 = self.get_var()
        self._stack.append(f"WITH {vars}, collect({tmp}) AS {var2}")
        return var2

    def get_var(self):
        self.current_var += 1
        return Var("var" + str(self.current_var))

    def get_tmp(self):
        self.current_tmp += 1
        return Var("tmp" + str(self.current_tmp))

    def get_simple_with(self):
        return ', '.join("var"+str(i) for i in range(1,self.current_var+1))

    def node_input_argument(self, input_arg):
        if self.current_state > MATCH:
            raise NotImplementedError()

        var = self.get_var()
        suquery = f"MATCH ({var})"
        where = f"{var}.name={quote(input_arg['name'])}"
        self.current_where.append(where)
        self._stack.append(suquery)
        return var

    def edge_input_argument(self, input_arg):
        raise NotImplementedError()

    def line_input_argument(self, input_arg):
        if self.current_state > MATCH:
            raise NotImplementedError()

        tmp = self.get_tmp()
        suquery = f"CALL apoc.create.vNodes(['LINE'], [{{id:'{input_arg}'}}]) yield node as {tmp}"
        self._stack.append(suquery)
        return self.do_match_to_with_transition(f"{tmp}")


    def subtract(self, a: Var, b: Var):
        subquery = f"{a} - {b}"
        return self.do_match_to_with_transition(subquery) if self.current_state < WITH else subquery

    def unique(self, a: Var):
        var = self.get_var()
        tmp = self.get_tmp()
        tmp1 = self.get_tmp()
        self._stack.append(f"UNWIND {a} as {tmp} WITH DISTINCT {tmp} as {tmp1} "
                           f"WITH collect({tmp1}) as {var} ")
        return var

    def count(self, a: Var):
        subquery = f"length({a}) "
        return self.do_match_to_with_transition(subquery) if self.current_state < WITH else subquery

    def pick(self, a: Var, prop: str):
        subquery = f"{a}.{unquote(prop)}"
        return self.do_match_to_with_transition(subquery) if self.current_state < WITH else subquery

    def shortest_path(self, a: Var, b: Var):
        if self.current_state > MATCH:
            raise NotImplementedError()

        tmp = self.get_tmp()
        suquery = f"MATCH {tmp} = shortestPath(({a})-[*]-({b})) "
        self._stack.append(suquery)

        var = self.do_match_to_with_transition(f"nodes({tmp}) ")
        return var

    def station(self, a: Var):
        return a

    def line(self, a: Var):
        return a["name"]

    def architecture(self, a: Var):
        return a

    def cleanliness(self, a: Var):
        return a

    def boolean(self, a: Var):
        return a

    def filter(self, query_var: Var, property: str, target: Var):
        if self.current_state > MATCH:
            raise NotImplementedError()

        where = f"{query_var}.{property} == {target}"
        self.current_where.append(where)
        return query_var

    def pluck(self, query_var: Var, property: str):
        vars = self.get_simple_with()
        var = self.get_var()
        tmp = self.get_tmp()
        self._stack.append(f"UNWIND {query_var} as {tmp} WITH {vars}, "
                           f"collect({tmp}.{unquote(property)}) AS {var} ")
        return var

    def _recurse(self, fp):
        if isinstance(fp, dict) and len(fp) != 1:
            return self.input_argument(fp)

        if not isinstance(fp, dict):
            return cypherencode(cypherparse(fp))

        assert len(fp) == 1, "Functional program can only contain a single function at a time, found {}".format(fp)
        operation, args = fp.popitem()

        return self.ops[operation](*(self._recurse(arg) for arg in args))

    def _do_where_clause(self):
        if self.current_where:
            self._stack.append(f"WHERE {' AND '.join(self.current_where)} ")
            self.current_where = []

    def do_match_to_with_transition(self, subquery):
        self._do_where_clause()

        var = self.get_var()
        self._stack.append(f"WITH {subquery} AS {var}")
        self.current_state = WITH
        return var

    def do_with_to_match_transition(self):
        self.current_state = MATCH

    def build(self):
        return_var = self._recurse(self.fp)

        self._stack.append(f"RETURN {return_var}")
        query = ' '.join(self._stack)
        return query
