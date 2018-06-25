

import yaml
from neo4j.exceptions import CypherError

from .graph_builder import GraphBuilder
from .gql_builder import GqlBuilder
from neo4j.v1 import GraphDatabase

def load_qas(qa_yaml="./data/test_qs.yaml"):
    with open(qa_yaml, "r") as file:
        for qa in yaml.load_all(file):
            yield qa


def load_london():
    with open("./data/london.yaml", "r") as file:
        london = yaml.load(file)

    with open("./data/london.yaml", "r") as file:
        london_all = list(yaml.load_all(file))
        assert len(london_all) == 1, "Yaml file only contains one object"

    print("loaded London")
    return london


def answer_question(gqa):

    question = gqa['question']
    print(question['english'])
    functional_question = question['functional']
    gb = GqlBuilder(functional_question)
    print(functional_question)
    try:
        query = gb.build()
    except NotImplementedError as e:
        print("ERROR building query: Not Implemented", e)
        return
    except Exception as e:
        print(e)
        raise
    print(query)
    result = list(session.read_transaction(lambda tx: tx.run(query)))
    if len(result) == 0:
        print("ERROR: No result")
        result = [[]]
    elif len(result) > 1:
        result = [[r[0] for r in result]]
    else:
        result = result[0]

    # print(result)
    try:

        answer = gqa['answer']
        print(result)
        if isinstance(answer, list):
            assert set(result[0]) == set(answer) or answer == [result[0]], f"{result} != {answer}"
        else:
            assert result[0] == answer or result[0] == [answer], f"{result} != {answer}"
        print(f"Answer: {result} (correct!)")
    except AssertionError as e:
        print(e)
        raise
    except CypherError as e:
        print(e)
        raise
    except Exception as e:
        print(e)
        raise



def nuke_neo(session):
    session.write_transaction(lambda tx: tx.run("MATCH ()-[r]-() delete r"))
    session.write_transaction(lambda tx: tx.run("MATCH (n) delete n"))

if __name__ == "__main__":

    url = "bolt://localhost:7687"
    user = "neo4j"
    password = "clegr-secrets"
    insecure = True
    driver = GraphDatabase.driver(url, auth=(user, password), encrypted=not insecure)
    session = driver.session()


    try:

        for qa in load_qas():
            nuke_neo(session)
            gb = GraphBuilder(qa)

            for insert_statement in gb.generate_node_inserts():
                print(insert_statement)
                session.write_transaction(lambda tx: tx.run(insert_statement))

            for insert_statement in gb.generate_edge_inserts():
                print(insert_statement)
                session.write_transaction(lambda tx: tx.run(insert_statement))

            print("graph created")

            answer_question(qa)

    finally:
        session.close()