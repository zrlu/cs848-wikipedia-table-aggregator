# -*- coding: utf-8 -*-

import rdflib
import io
import sys
from rdflib.namespace import FOAF, XSD, RDF

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

g = rdflib.Graph()

DBO = rdflib.Namespace("http://dbpedia.org/ontology/")
DBR = rdflib.Namespace("http://dbpedia.org/resource/")
DBP = rdflib.Namespace("http://dbpedia.org/property/")

g.load(DBR.term("Kobe_Bryant"))
g.load(DBR.term("Michael_Jordan"))

ask = "ASK { <http://dbpedia.org/ontology/" + "Kobe_Bryant" + "> ?s ?o \}"

qres = g.query(
    
"""
SELECT ?name ?birth
WHERE
{
    ?person foaf:name ?name .
    ?person dbo:birthDate ?birth .
}
"""
,
initNs={'foaf': FOAF, 'dbo': DBO, 'dbr': DBR, 'dbp': DBP, 'xsd': XSD, 'rdf': RDF}
)

for row in qres:
    print(row)