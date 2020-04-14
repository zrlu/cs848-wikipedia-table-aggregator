# -*- coding: utf-8 -*-

import rdflib
import io
import sys
from rdflib.namespace import FOAF, XSD, RDF
from rdflib.plugins.sparql import prepareQuery
import requests
import json
from wikitable import WikiTable, WikiPage
from logger import get_logger
import os
import multiprocessing
import urllib
from SPARQLWrapper import SPARQLWrapper, JSON
from collections import defaultdict

with open('nba.sparql', 'r') as f:
    query_string = f.read()
    sparql = SPARQLWrapper("http://dbpedia.org/sparql")
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
    LOGGERS[current_p.name] = get_logger(current_p.name, current_p.name + '.log', level='ERROR')

def func(args):
    name, url = args
    current_p = multiprocessing.current_process()
    wiki_page = WikiPage(url, LOGGERS[current_p.name])
    wiki_page.parse_tables()
    wiki_page.save(os.path.join(dump_path, name.encode('ascii', 'replace').decode('ascii') ))

pool = multiprocessing.Pool(16, initializer=init_worker)
pool.map(func, pairs)
pool.close()
pool.join()
