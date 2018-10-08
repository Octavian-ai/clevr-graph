from typing import Dict, Any, List, AnyStr
from .graph_builder import cypherencode, cypherparse, quote
from gqa.types import NodeSpec, EdgeSpec, LineSpec
import copy

class Var(object):
    def __init__(self, str: str, val: int):
        self.val = val
        self.str = str

    def __str__(self):
        return f"{self.str}{self.val}"

    def __eq__(self, other):
        return isinstance(other, Var) and self.val == other.val and self.str == other.str



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
            "GetLines": self.get_lines,
            "HasIntersection": self.has_intersection,
            "Filter": self.filter,
        }

        self.op_inputs = {
            "Station": self.node_input_argument,
            "Line": self.line_input_argument
        }

        self.current_var = 0
        self.first_usable_var = 1
        self.current_tmp = 0
        self.current_where = []
        self.current_state = MATCH
        self.specials = []
        self.unusable_vars = []

    def allEdges(self):
        if self.current_state > MATCH:
            raise NotImplementedError()

        var = self.get_var()
        subquery = f"MATCH ()-[{var}]-() "
        self._stack.append(subquery)
        return var

    def nodes(self, a: Var):
        self.unusable_vars.append(a)
        vars = self.get_all_vars()
        var = self.get_var()
        if self.current_state == MATCH:
            self._do_where_clause()
        if self.current_state == WITH:
            self.do_with_to_match_transition()
        self._stack.append(f"MATCH ({var})-[{a}]-()")
        return var

    def edges(self, a: Var):
        self.unusable_vars.append(a)

        var = self.get_var()
        if self.current_state == MATCH:
            self._do_where_clause()
        if self.current_state == WITH:
            self.do_with_to_match_transition()
            var = self.get_var()
        self._stack.append(f"MATCH ({a})-[{var}]-()")

        return var

    def get_lines(self, a: Var):
        if self.current_state == MATCH:
            self._do_where_clause()
        if self.current_state == WITH:
            self.do_with_to_match_transition()

        var = self.get_var()
        var2 = self.get_var()
        self._stack.append(f"MATCH ({a})-[{var2}]-(), ({var}:LINE)")
        self.current_where.append(f"{var2}.line_id ="
                                  f" {var}.id")
        var = self.get_var()
        self._stack.append(f"WITH {vars}, {var}")
        return var

    def has_intersection(self, a: Var, b: Var):
        self.unusable_vars.append(a)
        self.unusable_vars.append(b)
        if self.current_state == MATCH:
            self._do_where_clause()
        if self.current_state == WITH:
            pass
        vars = self.get_all_vars()
        var = self.get_var()
        self._stack.append(f"WITH {vars}, "
                           f"length(apoc.coll.intersection(collect({a}), collect({b}))) > 0 "
                           f"AS {var}")
        return var

    def get_var(self):
        self.current_var += 1
        return Var("var", self.current_var)

    def get_tmp(self):
        self.current_tmp += 1
        return Var("tmp", self.current_tmp)

    def get_all_vars(self):
        def usable_vars():
            yield "1 AS foo"
            for i in range(self.first_usable_var,self.current_var+1):
                var = Var('var', i)
                if var in self.unusable_vars:
                    continue
                yield var
        return ', '.join(str(x) for x in usable_vars())

    def node_input_argument(self, input_arg):
        if self.current_state > MATCH:
            self.do_with_to_match_transition()

        var = self.get_var()
        suquery = f"MATCH ({var})"
        where = f"{var}.name={quote(input_arg['name'])}"
        self._stack.append(suquery)
        self.current_where.append(where)
        return var

    def edge_input_argument(self, input_arg):
        raise NotImplementedError()

    def line_input_argument(self, input_arg):
        if self.current_state > MATCH:            raise NotImplementedError()

        var = self.get_var()
        suquery = f"MATCH ({var}:LINE)"
        where = f"{var}.name={quote(input_arg['name'])}"
        self._stack.append(suquery)
        self.current_where.append(where)
        return var


    def subtract(self, a: Var, b: Var):
        subquery = f"{a} - {b}"
        return self.do_match_to_with_transition(subquery) if self.current_state < WITH else subquery

    def unique(self, a: Var):
        if self.current_state < WITH:
            a = self.do_match_to_with_transition(f"{a}")

        self.unusable_vars.append(a)

        vars = self.get_all_vars()
        var = self.get_var()

        tmp = self.get_tmp()

        self._stack.append(f"WITH DISTINCT {a} as {var}, {vars} ")
        return var

    def count(self, a: Var):
        subquery = f"length(collect({a})) "
        return self.do_match_to_with_transition(subquery) if self.current_state < WITH else subquery

    def pick(self, a: Var, prop: str):
        subquery = f"{a}.{unquote(prop)}"
        return self.do_match_to_with_transition(subquery) if self.current_state < WITH else subquery

    def shortest_path(self, a: Var, b: Var, fallback):
        if self.current_state > MATCH:
            raise NotImplementedError()

        tmp = self.get_tmp()
        suquery = f"MATCH {tmp} = shortestPath(({a})-[*]-({b})) "
        self._stack.append(suquery)

        var = self.do_match_to_with_transition(f"{tmp}")
        var2 = self.get_var()
        self._stack.append(f"UNWIND nodes({var}) AS {var2} ")

        return var2

    def station(self, a: Var):
        return a

    def line(self, a: Var):
        return a

    def architecture(self, a: Var):
        return a

    def cleanliness(self, a: Var):
        return a

    def boolean(self, a: Var):
        return a

    def filter(self, query_var: Var, property: str, target: Var):
        if self.current_state > MATCH:
            self.do_with_to_match_transition()


        where = f"{query_var}.{unquote(property)} = {target}"
        self.current_where.append(where)
        return query_var

    def pluck(self, query_var: Var, property: str):
        self.unusable_vars.append(query_var)
        vars = self.get_all_vars()
        var = self.get_var()

        self._stack.append(f"WITH {vars}, {query_var}.{unquote(property)} AS {var} ")
        return var

    def _recurse(self, fp):
        if not isinstance(fp, dict):
            return cypherencode(cypherparse(fp))

        assert len(fp) == 1, "Functional program can only contain a single function at a time, found {}".format(fp)

        operation, args = fp.popitem()

        if operation not in self.ops:
            raise NotImplementedError(operation)

        fn_to_call = self.ops[operation]

        if operation in self.op_inputs:
            arguments = list(self.op_inputs[operation](arg) for arg in args)
        else:
            arguments = list(self._recurse(arg) for arg in args)

        for arg in arguments:
            if isinstance(arg, Var):
                self.unusable_vars.append(arg)
        result = fn_to_call(*arguments)

        return result

    def _do_where_clause(self):
        if self.current_where:
            self._stack.append(f"WHERE {' AND '.join(self.current_where)} ")
            self.current_where = []

    def do_match_to_with_transition(self, subquery):
        self._do_where_clause()

        vars = self.get_all_vars()
        var = self.get_var()

        self._stack.append(f"WITH {vars}, {subquery} AS {var}")
        self.current_state = WITH
        return var

    def do_with_to_match_transition(self):
        self.current_state = MATCH

    def build(self):
        return_var = self._recurse(self.fp)

        self._stack.append(f"RETURN {return_var}")
        query = ' '.join(self._stack)
        return query
