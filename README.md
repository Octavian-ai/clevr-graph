# CLEVR graph: A dataset for graph question answering

A graph question answering (GQA) dataset inspired by [CLEVR](https://cs.stanford.edu/people/jcjohns/clevr/). You could call it CLEGR. We aim to follow a similar methodology and usefulness.

<img src="https://raw.githubusercontent.com/davidsketchdeck/clevr-graph/master/assets/example2_qa.png"/>

The graph data is modelled on transit networks (e.g. the London tube and train network). Questions are modelled on questions typically asked around mass transit (e.g. How many stops between? Where do I change?). Our aim is that a successful solution to this dataset has real world applications.

## Download the data

[Download the full dataset](https://drive.google.com/open?id=1r2BS07_2lB25Vlo6a9HiafewTGENmI80)

## Content

This dataset contains a set of graph, question, answer tuples where
- graph is a generated transit graph (vaguely modelled on the London underground)
- question is posed in English, a functional program and Cypher
- answer is a number, boolean, list or categorical answer

## Questions

`python -m gqa.list_questions` lists the currently supported questions:

 - How clean is {Station}?
 - What is the cleanliness level of {Station} station?
 - How big is {Station}?
 - What size is {Station}?
 - What music plays at {Station}?
 - At {Station} what sort of music plays?
 - What architectural style is {Station}?
 - Describe {Station} station's architectural style.
 - Does {Station} have disabled access?
 - Is there disabled access at {Station}?
 - Does {Station} have rail connections?
 - Can you get rail connections at {Station}?
 - How many stations are between {Station} and {Station}?
 - Are {Station} and {Station} adjacent?
 - Which {Architecture} station is adjacent to {Station}?
 - Are {Station} and {Station} connected by the same station?
 - Is there a station called {Station}?
 - Is there a station called {FakeStationName}?
 - Which station is adjacent to {Station} and {Station}?
 - How many architectural styles does {Line} pass through?
 - How many music styles does {Line} pass through?
 - How many sizes of station does {Line} pass through?
 - How many stations playing {Music} does {Line} pass through?
 - How many {Cleanliness} stations does {Line} pass through?
 - How many {Size} stations does {Line} pass through?
 - How many stations with disabled access does {Line} pass through?
 - How many stations with rail connections does {Line} pass through?
 - Which lines is {Station} on?
 - How many lines is {Station} on?
 - Which stations does {Line} pass through?
 - Which line has the most {Architecture} stations?
 - Are {Station} and {Station} on the same line?
 - What's the nearest station to {Station} with disabled access?

Pull requests adding new questions are very welcome!

See a full list of the question definitions in [the source code](https://github.com/Octavian-ai/clevr-graph/blob/master/gqa/questions.py).

### Types of skills involved in answering questions

Fundamental skills:

- Counting nodes
- Counting edges
- Recalling property of node

Multi-step reasoning:

- Combining facts arithmetically (additon, counting) and logically (and, or)
- Traversing graph (repeated edge / node recall based on current memory)
- Comparison of data

### Potential new questions

Here are some questions that might be interesting to add to the dataset:

- What is the {biggest/cleanest} station {count} stops away from {Station}
- Are {Station} and {Station} connected by the same line as {Station} is on?
- What {Property} station is on {Line} and {Line}?
- Can I get from {Station} to {Station} only via {Property} stations?

## Data format

The entire dataset is stored in files `/data/gqa-xxxxxx.yaml`. This is a series of documents (i.e. YAML objects seperated by '---') to enable parallel parsing. Each document has the following structure: 

```yaml
answer: 7
graph: {...}
question: {...}

```

The structure of `graph` and `question` are explained below.


### Graph data

Graphs are a list of nodes and a list of edges. Each node represents a station. Each edge represents a line going between stations. A list of the different lines is also included for convenience.

Here is an example graph object:
```yaml
graph:
  id: 058af99c-bddc-48d3-a43b-a07cdc6a27ff
  nodes:
  - {architecture: glass, cleanliness: clean, disabled_access: true, has_rail: false, 
     id: 5ef607f3-7c54-484d-abc7-ae22030bf513, music: country, name: Stub Grove, size: small, 
     x: -2.9759803148208315, y: -0.5997361666284166}
  edges:
   - {line_color: gray, line_id: 3299ecda-ab86-483b-a0dd-d88ff0f03b0b,
      line_name: Gray Vuss, line_stroke: dotted, station1: 5ef607f3-7c54-484d-abc7-ae22030bf513,
      station2: 26fd3fc5-b447-4ade-929f-2b947abb8be0}
  lines:
  - {built: 90s, color: green, has_aircon: false,
    id: 37ed4b53-b696-4547-9b33-132cce0f2fa4, name: Green Gloot, stroke: dotted}
```


### Question data

Questions contain an english question, a functional representation of that question, a cypher query and the type of question.

Functional programs are represented as a syntax tree. For example the algebraic expression `subtract(count(shortest_path(Station(King's Cross), Station(Paddington))),2)` would be stored as:

```yaml
question:
  english: How many stations are between King's Cross and Paddington?
  functional:
    Subtract:
    - Count:
      - ShortestPath:
        - Station:
          - { name: King's Cross, ... }
        - Station:
          - { name: Paddington, ... }
    - 2
  type_string: StationShortestCount
  type_id: 1
  cypher: MATCH (var1) MATCH (var2) MATCH tmp1 = shortestPath((var1)-[*]-(var2))  WHERE
    var1.id="c2b8c082-7c5b-4f70-9b7e-2c45872a6de8" AND var2.id="40761fab-abd2-4acf-93ae-e8bd06f1e524"  WITH
    nodes(tmp1)  AS var3 RETURN length(var3)  - 2
```

## Statistics

<table>
  <tr><td>Number of (Graph,Question,Answer) triples</td><td>10,000</td></tr>
  <tr><td>Average number of lines per graph</td><td>20</td></tr>
  <tr><td>Average number of stations per graph</td><td>440</td></tr>
  <tr><td>Average number of edges per graph</td><td>420</td></tr>
  <tr><td>Number of question types</td><td>21</td></tr>
</table>

## Generation

You can randomly generate your own unique CLEVR graph dataset:
```shell
pipenv install
pipenv shell
python -m gqa.generate --count 10
```

The code is single threaded. If you run multiple processes in parallel then `cat` their output together, you can use all your CPU cores :)

## English, Functional and Cypher questions

We've included questions in three forms - English, a functional program and a Cypher query. We hope these can help with intermediary solutions, e.g. translating English into Cypher then executing the query, or translating the English into a functional program and then using Neural modules to compute it.

## Testing with Neo4J and Cypher

The `gql` directory contains code to:
 - Translate functional programs into Cypher queries
 - Upload the graphs to a Neo4j database
 - Verify that the Cypher query against the database gives the correct answer

### Usage

Start a neo4j enterprise instance with expected ports and credentials
N.b. By running this you are accepting the Neo4j Enterprise License Agreement 
```
docker run -it -p 7474:7474 -p 7687:7687 --env NEO4J_ACCEPT_LICENSE_AGREEMENT=yes --env NEO4J_AUTH=neo4j/clegr-secrets andrewjefferson/myneo4j:3.4.1-enterprise-plus-apoc
```

To load the first graph from `qga.yaml` into your Neo4j database (n.b. this will pre-emptively wipe your neo4j database, use with care):
```
python -m gql.load
```

## Contributing

We're an open-source organisation and are enthusiastic to collaborate with other researchers. Extending this dataset to a wider range of networks, questions or formats is very welcome.

## Acknowledgements

- All the contributors to [CLEVR](https://cs.stanford.edu/people/jcjohns/clevr/) and their supporters
- [Nicola Greco](https://twitter.com/nicolagreco), [Tubemaps](https://github.com/nicola/tubemaps) for the London tube map
- Thanks to Andrew Jefferson and Ashwath Salimath for their help with this project

## Citation

- D. Mack, A. Jefferson. CLEVR graph: A dataset for graph question answering, 2018

