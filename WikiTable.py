# -*- coding: utf-8 -*-

import requests
from bs4 import BeautifulSoup as BS, NavigableString, Tag
import pprint
import sys
import io
import operator
from collections import UserList
from prettytable import PrettyTable
from HTMLTableParser import HTMLTableParser
from logger import get_logger
import argparse
import csv
import os
import re
import urllib

class WikiTable:

    JOIN = 'JOIN'
    LAST = 'LAST'
    
    def __init__(self, soup, log):
        self.soup = soup
        self.title = None
        self.headers = []
        self.columns = []
        self.unmerged_table = []
        self.isvalid = False
        self.log = log
        self.string_headers_type = self.JOIN
    
    def clean_text(self, text):
        return text.strip().replace("*", "").replace("†", "").replace("~", "")

    def is_float(self, value):
        try:
            float(value)
            return True
        except TypeError:
            return False
        except ValueError:
            return False

    def is_int(self, value):
        try:
            int(value)
            return True
        except TypeError:
            return False
        except ValueError:
            return False

    def extract_header_cell(self, element):
        abbr = element.find('abbr')
        if abbr:
            return abbr.get('title').strip()
        sups = element.find_all("sup")
        if sups:
            for sup in sups:
                sup.decompose()
        return element.text.strip()

    def extract_data_cell(self, element):
        sups = element.find_all("sup")
        if sups:
            for sup in sups:
                sup.decompose()
        text = self.clean_text(element.text)
        comma_removed_text = text.replace(',', '')
        if self.is_float(comma_removed_text):
            return float(comma_removed_text)
        if self.is_int(text):
            return int(comma_removed_text)
        table = element.find("table") # nested table?
        if table:
            texts = []
            for cell in table.find_all("td"):
                texts.append(self.extract_data_cell(cell))
            return "; ".join(texts)
        if text == "":
            children = list(element.children)
            for child in children:
                if child.name == 'span':
                    if child.get('title'):
                        return child.get('title')
        return text

    def is_row_th(self, th):
        return th.get("scope") == 'row'

    def parse_headers(self):
        headers = []
        row_idx = 0
        while 1:
            row = []
            stop = False
            for col in self.unmerged_table:
                cell = col[row_idx]
                if cell.name == 'td':
                    stop = True
                    break
                if cell.name == 'th':
                    row.append(self.extract_header_cell(cell))
            if stop:
                row_idx -= 1
                break
            if row:
                headers.append(row)
            row_idx += 1

        if not headers:
            raise Exception("Header not found.")

        return list(map(list, zip(*headers))), row_idx
 
    def is_summary_row(self, row):
        for data in row:
            if type(data) == str:
                if re.match(re.compile('sum|average|total|turnout|majority|summary|career|all-star', re.IGNORECASE), data) is not None:
                    return True, data
        return False, None

    def remove_row(self, i):
        for col in self.columns:
            del col[i]

    def tag_count(self, tags, tagname):
        count = 0
        for tag in tags:
            if tag.name == tagname:
                count += 1
        return count

    def parse_data(self, row_idx):
        columns = []
        
        for col in self.unmerged_table:
            columns.append(list(map(self.extract_data_cell, col[row_idx+1:])))

        return columns

    def remove_empty_columns(self):
        headers_to_remove = []
        cur = 0
        while cur < self.count_cols():
            if all(map(lambda value: value == '', self.columns[cur])):
                headers_to_remove.append(self.headers[cur])
                del self.columns[cur]
            cur += 1
        for h in headers_to_remove:
            self.headers.remove(h)
    
    def remove_summary_rows(self):
        cur = 0
        removed = 0
        old_idx = 0
        while cur < self.count_rows():
            is_summary, s = self.is_summary_row(self.get_row(cur))
            if is_summary:
                self.log.info("Row {} looks like a summary row with keyword '{}', removed.".format(old_idx+1, s))
                self.remove_row(cur)
                removed += 1
                old_idx += 1
                continue
            cur += 1
            old_idx += 1
        self.log.info("Removed {} summary rows.".format(removed))

    def parse(self):
        try:
            parser = HTMLTableParser()
            parser.parse_soup(self.soup)
            self.unmerged_table = parser.get_columns()
        except Exception as e:
            self.log.warn(e)
            self.log.warn("HTMLTableParser: unable to parse raw html table.")
            return False
        try:
            self.headers, row_idx = self.parse_headers()
            self.log.debug(self.headers)
        except Exception as e:
            self.log.warn(e)
            self.log.warn("Unable to parse header.")
            return False
        try:
            self.columns = self.parse_data(row_idx)
        except Exception as e:
            self.log.warn(e)
            self.log.warn("Unable to parse data.")
            return False

        self.remove_empty_columns()
        self.log.debug(self.headers)
        self.log.debug(self.columns)
        nattr = len(self.headers)

        if nattr == 0:
            self.log.warn("Discarding tables without a header.")
            self.isvalid = False
            return False
        if nattr == 1:
            self.log.warn("Discarding tables with only 1 column.")
            self.isvalid = False
            return False
        if nattr != len(self.columns):
            self.log.warn("The number of attributes does not match with the number of columns.")
            self.log.warn("The number of attributes is {}".format(nattr))
            self.log.warn("The number of columns is {}".format(len(self.columns)))
            self.log.debug("Headers: ")

            first_N_rows = min(10, len(self.columns[0]))
            self.log.debug("First {} rows: ".format(first_N_rows))
            for k in range(first_N_rows):
                self.log.debug("Row {}: {}".format(k, [self.columns[i][k] for i in range(len(self.columns))]))
            return False
        if not all(len(self.columns[0]) == len(col) for col in self.columns):
            self.log.warn("Columns don't have the same number of entries. Expect {}".format(len(self.columns[0])))
            return False

        unique_headers = set()
        for header in self.string_headers():
            if header not in unique_headers:
                unique_headers.add(header)
            else:
                self.log.warn("Duplicate header '{}' found.".format(header))
                self.log.debug(header)
                return False

        self.remove_summary_rows()

        self.isvalid = True
        return True
    
    def string_headers(self):
        if self.string_headers_type == self.JOIN:
            return [":".join(header) for header in self.headers]
        return [header[-1] for header in self.headers]

    def count_rows(self):
        return len(self.columns[0])
    
    def count_cols(self):
        return len(self.columns)
    
    def get_row(self, i):
        row = [self.columns[j][i] for j in range(self.count_cols())]
        return row

    def iter_row(self):
        for i in range(self.count_rows()):
            yield self.get_row(i)
    
    def __iter__(self):
        return self.iter_row()

    def __str__(self):
        if not self.isvalid:
            return "INVALID TABLE"
        pt = PrettyTable(self.string_headers())
        for row in self.iter_row():
            pt.add_row(row)
        return str(pt)

class WikiPage:

    def __init__(self, url, log, showtable=True):
        self.url = url
        self.tables = []
        self.log = log
        self.showtable = showtable

    def parse_tables(self):
        self.log.info("GET " + self.url)
        r = requests.get(self.url)
        self.log.info("Response: {}".format(r.status_code))
        soup = BS(r.content, features="html.parser")
        tables = soup.findAll("table", attrs={"class": "wikitable"})
        self.log.info("{} tables are found.".format(len(tables)))
        nvalid = 0
        for i, t in enumerate(tables):
            self.log.info("Parsing table {}/{}...".format(i+1, len(tables)))
            wtable = WikiTable(t, self.log)
            wtable.parse()
            if wtable.isvalid:
                nvalid += 1
                self.tables.append(wtable)
                if self.showtable:
                    self.log.info("=== TABLE ({}/{}) ===".format(i+1, len(tables)))
                    self.log.info("Number of attributes: {}".format(wtable.count_cols()))
                    self.log.info("Number of rows: {}".format(wtable.count_rows()))
                    self.log.info("\n{}".format(str(wtable)))
                    self.log.info("=== END OF TABLE ===")
        self.log.info("{}/{} tables are valid.".format(nvalid, len(tables)))
    
    def save(self, outpath='.'):
        for i, wtable in enumerate(self.tables):
            self.log.debug("mkdir -p {}".format(outpath))
            os.makedirs(outpath, exist_ok=True)
            fp = os.path.join(outpath, 'table-{0:05d}.csv'.format(i))
            self.log.info("Write to file {}".format(fp))
            with open(fp, 'w', encoding='utf-8') as csvfile:
                writer = csv.writer(csvfile, dialect='excel')
                writer.writerow(wtable.string_headers())
                for row in wtable:
                    writer.writerow(row)

if __name__ == "__main__":

    parser = argparse.ArgumentParser(description='Fetch tables from a Wikipedia page.')
    parser.add_argument('URLs', metavar='URL', type=str, nargs='+',
                        help='the urls of the wikipedia page')
    parser.add_argument('-o', '--out', dest='outpath', type=str, default="",
                        help='the output path')
    parser.add_argument('-L', '--loglevel', dest='loglevel', type=str, default="INFO",
                        help="log level (default='INFO')", choices=('CRITICAL', 'ERROR', 'WARN', 'INFO', 'DEBUG'))
    parser.add_argument('--show-table', dest='showtable', action='store_true', help='print tables')
    parser.add_argument('--no-show-table', dest='showtable', action='store_false')
    parser.set_defaults(show=False)
    args = parser.parse_args()


    LOGGER = get_logger(WikiTable.__class__.__name__, 'job.log')

    for url in args.URLs:
        page_name = url.split("/")[-1]
        page = WikiPage(url, LOGGER, showtable=args.showtable)
        page.parse_tables()
        if args.outpath:
            page.save(os.path.join(args.outpath, page_name))