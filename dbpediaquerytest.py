# -*- coding: utf-8 -*-

import rdflib
import io
import sys
from rdflib.namespace import FOAF, XSD, RDF
from rdflib.plugins.sparql import prepareQuery
import requests
import json
from WikiTable import WikiTable, WikiPage
from logger import get_logger
import os
import multiprocessing
import urllib
from SPARQLWrapper import SPARQLWrapper, JSON
from collections import defaultdict

# DBO = rdflib.Namespace("http://dbpedia.org/ontology/")
# DBR = rdflib.Namespace("http://dbpedia.org/resource/")
# DBP = rdflib.Namespace("http://dbpedia.org/property/")

# query = prepareQuery(
# """
# SELECT DISTINCT ?name ?url
# WHERE
# {
#     ?person foaf:name ?name .
#     ?person a dbo:BasketballPlayer .
#     ?person dbp:nba ?nba .
#     ?person foaf:isPrimaryTopicOf ?url
# }
# GROUP BY $url
# """
# ,initNs={'foaf': FOAF, 'dbo': DBO, 'dbr': DBR, 'dbp': DBP, 'xsd': XSD, 'rdf': RDF}
# )

sparql = SPARQLWrapper("http://dbpedia.org/sparql")

query_string = """
PREFIX foaf: <http://xmlns.com/foaf/0.1/>
PREFIX dbo: <http://dbpedia.org/ontology/>
PREFIX xsd: <http://www.w3.org/2001/XMLSchema#>
PREFIX rdf: <http://www.w3.org/2000/01/rdf-schema#>
PREFIX dbp: <http://dbpedia.org/property/>
PREFIX dbr: <http://dbpedia.org/resource/>

SELECT DISTINCT ?name ?url
WHERE
{
    ?person foaf:name ?name .
    ?person a dbo:BasketballPlayer .
    ?person dbp:nba ?nba .
    ?person foaf:isPrimaryTopicOf ?url
}
GROUP BY $url
"""

sparql.setQuery(query_string)
sparql.setReturnFormat(JSON)
data = sparql.query().convert()

dump_path = 'dump'
bindings = data['results']['bindings']

pairs = []
for binding in bindings:
    name = binding['name']['value']
    url = binding['url']['value']
    pairs.append((name, url))

LOGGERS = {}

def init_worker():
    current_p = multiprocessing.current_process()
    LOGGERS[current_p.name] = get_logger(current_p.name, current_p.name + '.log', level='INFO')

def func(args):
    name, url = args
    current_p = multiprocessing.current_process()
    wiki_page = WikiPage(url, LOGGERS[current_p.name])
    wiki_page.parse_tables()
    wiki_page.save(os.path.join(dump_path, name.encode('ascii', 'replace').decode('ascii') ))

pool = multiprocessing.Pool(1, initializer=init_worker)
pool.map(func, pairs)
pool.close()
pool.join()
