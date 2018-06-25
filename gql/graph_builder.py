from typing import List, Dict, Any, Callable, Union, Tuple
import ast
import json
import sys

NeoTypes = Union[int, float, str]


def cypherparse(x: Any):
    if isinstance(x, str):
        try:
            parsed = ast.literal_eval(x)
        except:
            return x
        x = parsed

    if isinstance(x, NeoTypes.__args__):
        return x
    else:
        print("WARNING: unsupported type", x, str(x), file=sys.stderr)
        return str(x)


def cypherencode(v: NeoTypes):
    return quote(v) if isinstance(v, str) else v


def ALL_PROPERTIES(entity: Dict[str, Any]) -> Dict[str, NeoTypes]:

    return {k: cypherparse(v) for k, v in entity.items()}


def CONST_LABEL(label: str) -> Callable[[Dict[str, Any]], List[str]]:
    result = [label]

    def label_fn(entity: Dict[str, Any]):
        return result

    return label_fn


def FROM_TO(from_property: str, to_property: str) -> Callable[
    [Dict[str, Any]], Tuple[NeoTypes, NeoTypes]]:
    def route_fn(entity: Dict[str, Any]):
        return cypherparse(entity[from_property]), cypherparse(entity[to_property])

    return route_fn


def quote(x: str):
    return f'"{x}"'


class GraphBuilder(object):
    def __init__(self,
                 gqa,
                 node_label_fn: Callable[[Dict[str, Any]], List[str]] = CONST_LABEL("NODE"),
                 edge_label_fn: Callable[[Dict[str, Any]], List[str]] = CONST_LABEL("EDGE"),
                 node_prop_fn: Callable[[Dict[str, Any]], Dict[str, NeoTypes]] = ALL_PROPERTIES,
                 edge_prop_fn: Callable[[Dict[str, Any]], Dict[str, NeoTypes]] = ALL_PROPERTIES,
                 edge_route_fn: Callable[[Dict[str, Any]], Tuple[NeoTypes, NeoTypes]] = FROM_TO(
                     "station1", "station2")):
        super(GraphBuilder, self).__init__()
        self._edge_route_fn = edge_route_fn
        self._edge_prop_fn = edge_prop_fn
        self._node_prop_fn = node_prop_fn
        self._edge_label_fn = edge_label_fn
        self._node_label_fn = node_label_fn
        self.gqa = gqa
        self.graph = gqa['graph']

    def generate_node_inserts(self):
        for node in self.graph['nodes']:
            labels = self._node_label_fn(node)
            props = self._node_prop_fn(node)

            props = ', '.join(
                f'{k}: {quote(v) if isinstance(v, str) else v}' for k, v in props.items())
            template = f"CREATE (n:{':'.join(labels)} {{ {props} }})"
            yield template

        for line in self.graph['lines']:
            props = self._node_prop_fn(line)
            props = ', '.join(
                f'{k}: {quote(v) if isinstance(v, str) else v}' for k, v in props.items())
            template = f"CREATE (n:LINE {{ {props} }})"
            yield template

    def generate_edge_inserts(self):
        for edge in self.graph['edges']:
            labels = self._edge_label_fn(edge)
            assert len(labels) > 0, "edges must have at least one label"
            props = self._edge_prop_fn(edge)
            props = ', '.join(
                f'{k}: {cypherencode(v)}' for k, v in props.items()
            )
            from_id, to_id = self._edge_route_fn(edge)

            template = f"MATCH (from),(to) " \
                       f"WHERE from.id = {cypherencode(from_id)} " \
                       f"and to.id = {cypherencode(to_id)} " \
                       f"CREATE (from)-[l:{':'.join(labels)} {{ {props} }}]->(to)"

            yield template
