# -*- coding: utf-8 -*-

import requests
from bs4 import BeautifulSoup as BS, NavigableString, Tag
import pprint
import sys
import io
import operator
from collections import UserList
import logging
from prettytable import PrettyTable
import argparse
import csv
import os
import re

class WikiTable:

    JOIN = 'JOIN'
    LAST = 'LAST'
    
    def __init__(self, soup, logging):
        self.soup = soup
        self.title = None
        self.headers = []
        self.columns = []
        self.ndata = 0
        self.nattr = 0
        self.isvalid = False
        self.log = logging
        self.string_headers = []
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
        if self.is_float(text):
            return float(text)
        if self.is_int(text):
            return int(text)
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
        entries = []
        trs = self.soup.find_all('tr')
        nrow = 0
        nattr = 0
        for tr in trs:
            ths = tr.find_all('th')
            tds = tr.find_all('td')
            if list(tds) != []:
                break
            ncol = 0
            for th in ths:
                if self.is_row_th(th):
                    continue
                text = self.extract_header_cell(th)
                colspan = int(th.get("colspan", "1"))
                rowspan = int(th.get("rowspan", "1"))
                for ci in range(ncol, ncol + colspan):
                    for ri in range(nrow, nrow + rowspan):
                        entries.append((ri, ci, text))
                ncol += colspan
                nattr = max(nattr, ncol)
            nrow += 1

        entries.sort(key=operator.itemgetter(0, 1))

        log.debug('nrow={}'.format(nrow))

        if nattr == 0:
            raise Exception("Header not found.")

        n = len(entries) // nattr
        log.debug('parse_headers: nattr={}'.format(nattr))
        headers = [[] for i in range(nattr)]

        for i in range(n):
            for j in range(nattr):
                entry = entries[i*nattr+j]
                colname = entry[2]
                if headers[j] == [] or headers[j][-1] != colname:
                    headers[j].append(colname)
        return headers
 
    def is_summary_row(self, tr):
        if tr.find_all(text=re.compile('sum|average|total|turnout|majority', re.IGNORECASE)) != []:
            return True
        return False

    def parse_data(self):
        entries = []
        trs = self.soup.find('tbody').find_all('tr', recursive=False)
        nrow = 0
        nattr = 0
        for tr in trs:
            if 'sortbottom' in tr.get('class', []):
                continue
            if self.is_summary_row(tr):
                log.info("A summary row seems to be found, early break.")
                break
            ths = tr.find_all('th', recursive=False)
            tds = tr.find_all('td', recursive=False)
            if len(list(tds)) == 0:
                continue
            ncol = 0
            row_cells = ths + tds
            
            is_summary_row = False
            this_row_entries = []

            for cell in row_cells:
                text = self.extract_data_cell(cell)
                colspan = int(cell.get("colspan", "1"))
                rowspan = int(cell.get("rowspan", "1"))
                for ci in range(ncol, ncol + colspan):
                    for ri in range(nrow, nrow + rowspan):
                        this_row_entries.append((ri, ci, text))
                ncol += colspan
                nattr = max(nattr, ncol)

            entries += this_row_entries
            nrow += 1
        
        entries.sort(key=operator.itemgetter(0, 1))

        log.debug('parse_data: nattr={}'.format(nattr))

        n = len(entries) // nattr
        columns = [[] for i in range(nattr)]

        for i in range(n):
            for j in range(nattr):
                entry = entries[i*nattr+j]
                value = entry[2]
                columns[j].append(value)
        return columns

    def remove_empty_columns(self):
        headers_to_remove = []
        cur = 0
        ncol = len(self.columns)
        while cur < ncol:
            if all(map(lambda value: value == '', self.columns[cur])):
                del self.columns[cur]
                ncol = len(self.columns)
                headers_to_remove.append(self.headers[i])
            cur += 1
        for h in headers_to_remove:
            self.headers.remove(h)

    def parse(self):
        try:
            self.headers = self.parse_headers()
        except Exception as e:
            self.log.warn(e)
            self.log.warn("Unable to parse header.")
            return False
        try:
            self.columns = self.parse_data()
        except Exception as e:
            self.log.warn(e)
            self.log.warn("Unable to parse data.")
            return False

        self.remove_empty_columns()
        log.debug(self.headers)
        log.debug(self.columns)
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
        if self.string_headers_type == self.JOIN:
            string_headers = [":".join(header) for header in self.headers]
        else:
            string_headers = [header[-1] for header in self.headers]
        for header in string_headers:
            if header not in unique_headers:
                unique_headers.add(header)
            else:
                self.log.warn("Duplicate header '{}' found.".format(header))
                self.log.debug(header)
                return
        self.string_headers = string_headers
        self.nattr = nattr
        self.ndata = len(self.columns[0])
        self.isvalid = True
        return True
    
    def iter_row(self):
        for i in range(self.ndata):
            row = [self.columns[j][i] for j in range(self.nattr)]
            yield row
    
    def __iter__(self):
        return self.iter_row()

    def __str__(self):
        if not self.isvalid:
            return "INVALID TABLE"
        pt = PrettyTable(self.string_headers)
        for row in self.iter_row():
            pt.add_row(row)
        return str(pt)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Fetch tables from a Wikipedia page.')
    parser.add_argument('URLs', metavar='URL', type=str, nargs='+',
                        help='the urls of the wikipedia page')
    parser.add_argument('-o', '--out', dest='outpath', type=str, default=".",
                        help='the output path')
    parser.add_argument('-L', '--loglevel', dest='loglevel', type=str, default="INFO",
                        help="log level (default='INFO')", choices=('CRITICAL', 'ERROR', 'WARN', 'INFO', 'DEBUG'))
    parser.add_argument('--show', dest='show', action='store_true', help='print tables')
    parser.add_argument('--no-show', dest='show', action='store_false')
    parser.set_defaults(show=False)
    args = parser.parse_args()

    log = logging.getLogger(__name__)
    log.setLevel(args.loglevel)
    log.handlers.clear()
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')
    os.makedirs(args.outpath, exist_ok=True)
    logpath = os.path.join(args.outpath, 'job.log')
    formatter = logging.Formatter('%(asctime)s %(levelname)-8s [%(filename)s:%(lineno)d] %(message)s')
    fileHandler = logging.FileHandler(logpath, 'w', 'utf-8')
    fileHandler.setFormatter(formatter)
    stdErrHandler = logging.StreamHandler(sys.stderr)
    stdErrHandler.setFormatter(formatter)
    log.addHandler(fileHandler)
    log.addHandler(stdErrHandler)

    for url in args.URLs:
        log.info("GET " + url)
        r = requests.get(url)
        log.info("Response: {}".format(r.status_code))
        soup = BS(r.content, features="html.parser")
        tables = soup.findAll("table", attrs={"class": "wikitable"})
        log.info("{} tables are found.".format(len(tables)))
        nvalid = 0
        for i, t in enumerate(tables):
            log.info("Parsing table {}/{}...".format(i+1, len(tables)))
            wtable = WikiTable(t, log)
            wtable.parse()
            if wtable.isvalid:
                nvalid += 1
                if args.show:
                    log.info("=== TABLE ({}/{}) ===".format(i+1, len(tables)))
                    log.info("Number of attributes: {}".format(wtable.nattr))
                    log.info("Number of rows: {}".format(wtable.ndata))
                    log.info("\n{}".format(str(wtable)))
                    log.info("=== END OF TABLE ===")
                if args.outpath:
                    fp = os.path.join(args.outpath, 'table-{0:05d}.csv'.format(i))
                    log.info("Writing to file {} ...".format(fp))
                    with open(fp, 'w', encoding='utf-8') as csvfile:
                        writer = csv.writer(csvfile, dialect='excel')
                        writer.writerow(wtable.string_headers)
                        for row in wtable:
                            writer.writerow(row)
                
        log.info("{}/{} tables are valid.".format(nvalid, len(tables)))