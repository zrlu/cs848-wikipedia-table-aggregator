import rdflib
import io
import sys
from rdflib.namespace import FOAF, XSD, RDF
from rdflib.plugins.sparql import prepareQuery
import requests
import json
from WikiTable import WikiTable
import logging

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

DBO = rdflib.Namespace("http://dbpedia.org/ontology/")
DBR = rdflib.Namespace("http://dbpedia.org/resource/")
DBP = rdflib.Namespace("http://dbpedia.org/property/")

query = prepareQuery(
"""
SELECT ?name ?url
WHERE
{
    ?person foaf:name ?name .
    ?person a dbo:BasketballPlayer .
    ?person dbp:nba ?nba .
    ?person foaf:isPrimaryTopicOf ?url
}
"""
,initNs={'foaf': FOAF, 'dbo': DBO, 'dbr': DBR, 'dbp': DBP, 'xsd': XSD, 'rdf': RDF}
)

query_string = """
PREFIX foaf: <http://xmlns.com/foaf/0.1/>
PREFIX dbo: <http://dbpedia.org/ontology/>
PREFIX xsd: <http://www.w3.org/2001/XMLSchema#>
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>

SELECT ?name ?url
WHERE
{
    ?person foaf:name ?name .
    ?person a dbo:BasketballPlayer .
    ?person dbp:nba ?nba .
    ?person foaf:isPrimaryTopicOf ?url
}
"""

query_url = "http://dbpedia.org/sparql?default-graph-uri=http%3A%2F%2Fdbpedia.org&query=PREFIX+foaf%3A+%3Chttp%3A%2F%2Fxmlns.com%2Ffoaf%2F0.1%2F%3E%0D%0APREFIX+dbo%3A+%3Chttp%3A%2F%2Fdbpedia.org%2Fontology%2F%3E%0D%0APREFIX+xsd%3A+%3Chttp%3A%2F%2Fwww.w3.org%2F2001%2FXMLSchema%23%3E%0D%0APREFIX+rdfs%3A+%3Chttp%3A%2F%2Fwww.w3.org%2F2000%2F01%2Frdf-schema%23%3E%0D%0A%0D%0ASELECT+%3Fname+%3Furl%0D%0AWHERE%0D%0A%7B%0D%0A++++%3Fperson+foaf%3Aname+%3Fname+.%0D%0A++++%3Fperson+a+dbo%3ABasketballPlayer+.%0D%0A++++%3Fperson+dbp%3Anba+%3Fnba+.%0D%0A++++%3Fperson+foaf%3AisPrimaryTopicOf+%3Furl%0D%0A%7D&format=application%2Fsparql-results%2Bjson&CXML_redir_for_subjs=121&CXML_redir_for_hrefs=&timeout=30000&debug=on&run=+Run+Query+"
g = rdflib.Graph()
r = requests.get(query_url)
data = json.loads(r.content)

bindings = data['results']['bindings']
for b in bindings:
    print(b['name']['value'], b['url']['value'])
