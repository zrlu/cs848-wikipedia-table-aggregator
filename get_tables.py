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
from urllib.parse import urlparse
import argparse
import pdb

if __name__ == '__main__':

    parser = argparse.ArgumentParser(description='Fetch tables from a Wikipedia page.')

    parser.add_argument('-o', '--out', dest='outpath', type=str, default="",
                        help='the output path')
    parser.add_argument('-L', '--loglevel', dest='loglevel', type=str, default="INFO",
                        help="log level (default='INFO')", choices=('CRITICAL', 'ERROR', 'WARN', 'INFO', 'DEBUG'))

    subparsers = parser.add_subparsers(help='help for subcommand')

    parser_url = subparsers.add_parser('url', help='help for url subcommand')
    parser_url.add_argument('URL', metavar='URL', type=str, nargs='+',
                        help='the urls of the wikipedia page')

    parser_sparql = subparsers.add_parser('sparql', help='help for sparql subcommand')
    parser_sparql.add_argument('SPARQL', metavar='file', type=str,
                        help='the path to .sparql file')

  
    args = parser.parse_args()

    if hasattr(args, 'URL'):
        urls = args.URL

    if hasattr(args, 'SPARQL'):
        with open(args.SPARQL, 'r') as f:
            query_string = f.read()
            sparql = SPARQLWrapper("http://dbpedia.org/sparql")
            sparql.setQuery(query_string)
            sparql.setReturnFormat(JSON)
            data = sparql.query().convert()

        urls = [b['url']['value'] for b in data['results']['bindings']]
    
    LOGGERS = {}
    
    def init_worker():
        current_p = multiprocessing.current_process()
        LOGGERS[current_p.name] = get_logger(current_p.name, current_p.name + '.log', level='ERROR')

    def func(url):
        path = urlparse(url).path.encode('ascii', 'replace').decode('ascii')
        print('GET', path)
        os.makedirs(path, exist_ok=True)
        current_p = multiprocessing.current_process()
        wiki_page = WikiPage(url, LOGGERS[current_p.name])
        wiki_page.parse_tables()
        wiki_page.save(args.outpath + path)

    pool = multiprocessing.Pool(16, initializer=init_worker)
    pool.map(func, urls)
    pool.close()
    pool.join()
