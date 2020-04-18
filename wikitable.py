# -*- coding: utf-8 -*-

import requests
from bs4 import BeautifulSoup as BS, NavigableString, Tag
import pprint
import sys
import io
import operator
from prettytable import PrettyTable
from html_table import HTMLTableParser
from logger import get_logger
import argparse
import os
import re
import urllib
from rules import summary_row_keywords, cell_remove_special_symbols, cell_replace_special_symbols
import pandas as pd
import pdb
import unicodedata
from unidecode import unidecode 

# a class for parsing a single table in Wikipedia
class WikiTable:

    # a column name might be a list of strings because the header can be
    # hierarchical

    # if string_headers_type is JOIN, then a comma separated string will be
    # returned as header
    JOIN = 'JOIN'

    # otherwise, return the last string as header, which may result in duplicated
    # columns
    LAST = 'LAST'
    
    def __init__(self, soup, log, name='default_name'):
        self.soup = soup
        self.title = None
        self.headers = []
        self.columns = []
        self.unmerged_table = []
        self.dataframe = None
        self.isvalid = False
        self.log = log
        self.string_headers_type = self.JOIN
        self.name = name
    
    # tell the program how to clean the text
    def _clean_text(self, text):

        # replace some characters by another based on the rule
        for pattern, repl in cell_replace_special_symbols:
            text = re.sub(pattern, repl, text)

        # remove accents from a unicode string
        text = unidecode(text)

        # remove special symbols, like footnote symbols, based on the rule
        text = re.sub(cell_remove_special_symbols, '', text.strip())
        return text

    # try casting the string to float
    def _to_float(self, texts):
        try:
            return float(texts)
        except TypeError:
            return None
        except ValueError:
            return None

    # try casting the string to ints
    def _to_int(self, texts):
        try:
            return int(texts)
        except TypeError:
            return None
        except ValueError:
            return None

    # remove the citation element from the html node tree
    def _remove_reference(self, element):
        sups = element.find_all("sup")
        if sups:
            for sup in sups:
                sup.decompose()

    # extract header name from the header cell
    def _extract_header_cell(self, element):
        # just get what is displayed...although the abbr tag might containt column names
        # that makes much more sense
        #
        # abbr = element.find('abbr')
        # if abbr:
        #     return abbr.get('title').strip()
        return self._clean_text(element.text)
    
    # try casting a string to numeric
    def _to_numeric(self, text):
        no_comma = text.replace(',', '')
        return self._to_int(no_comma) or self._to_float(no_comma)

    # try parsing a string starting with dollar sign as numeric
    def _parse_currency(self, text):
        if text.startswith('$'):
            return self._to_numeric(text[1:].lstrip())
        return None
    
    # try parsing a string ending with percentage sign as numeric
    def _parse_percentage(self, text):
        if text.endswith('%'):
            return self._to_numeric(text[:1].rstrip()) / 100
        return None

    # some cell uses words like 'N/A', this function tells if a cell with such
    # value to None, but this function is not used for now
    def _is_not_available(self, text):
        return re.match(re.compile([], re.IGNORECASE), text) is not None

    # extract value a data cell
    def _extract_data_cell(self, element):

        # trim and clean the text first
        text = self._clean_text(element.text)

        # first, try if it can be converted to a numeric
        extracted = self._to_numeric(text)
        if extracted is not None:
            return extracted

        # next, try if it represents money
        extracted = self._parse_currency(text)
        if extracted is not None:
            return extracted

        # next, try if it is a percentage
        extracted = self._parse_percentage(text)
        if extracted is not None:
            return extracted

        # nested table?
        table = element.find("table")
        if table:
            # for now ignore tables inside a cell...
            #
            # texts = []
            # for cell in table.find_all("td"):
            #     texts.append(self.extract_data_cell(cell))
            # return "; ".join(texts)
            return None

        # if it is empty
        if not text:
            # some cells might contain non-text elements, the title attr should represent the value
            # but for now just ignore it
            #
            # children = list(element.children)
            # for child in children:
            #     if child.name == 'span':
            #         if child.get('title'):
            #             return child.get('title')
            return None

        return text

    # determine if it is a vertical header
    def _is_data_th(self, th):
        return th.get("scope") == 'row'

    # try parsing the headers
    def _parse_headers(self):
        headers = []
        row_idx = 0
        while 1:
            row = []
            stop = False
            for col in self.unmerged_table:
                cell = col[row_idx]
                if cell.name == 'td':
                    # if a row with td is reached, it is likely that the headers stops here
                    stop = True
                    break
                if cell.name == 'th':
                    if self._is_data_th(cell):
                        stop = True
                        break
                    string = self._extract_header_cell(cell)
                    # if a row with th cell is reached and contains numerics value, it is likely
                    # that the headers stops here
                    if self._to_numeric(string) is not None:
                        row_idx += 1
                        stop = True
                        break
                    row.append(string)
            if stop:
                row_idx -= 1
                break
            if row:
                headers.append(row)
            row_idx += 1

        if not headers:
            raise Exception("Header not found.")

        return list(map(list, zip(*headers))), row_idx
 
    # determine if a row is a summary row, if so, this should be removed
    def _is_summary_row(self, row):
        for data in row:
            if type(data) == str:
                if re.match(re.compile(summary_row_keywords, re.IGNORECASE), data) is not None:
                    return True, data
        return False, None

    # remove a row by its index
    def _remove_row(self, i):
        # because the data is stored as columns, remove the corresponding value
        # for all columns
        for col in self.columns:
            del col[i]

    # count the number of tags
    def _tag_count(self, tags, tagname):
        count = 0
        for tag in tags:
            if tag.name == tagname:
                count += 1
        return count

    # return the rows starting with row_index as data, in columns
    def _parse_data(self, row_idx):
        columns = []
        
        for col in self.unmerged_table:
            columns.append(list(map(self._extract_data_cell, col[row_idx+1:])))

        return columns

    # check if a value is empty
    def _is_empty(self, value):
        return value == '' or value is None
    
    # check if a list is empty values
    def _is_empty_list(self, lst):
        return all(map(lambda value: self._is_empty(value), lst))
    
    # remove all the summary rows
    def _remove_summary_rows(self):
        cur = 0
        removed = 0
        old_idx = 0
        while cur < self.count_rows():
            is_summary, s = self._is_summary_row(self.get_row(cur))
            if is_summary:
                self.log.info("Row {} looks like a summary row with keyword '{}', removed.".format(old_idx+1, s))
                self._remove_row(cur)
                removed += 1
                old_idx += 1
                continue
            cur += 1
            old_idx += 1
        self.log.info("Removed {} summary rows.".format(removed))

    # parse the wikipedia table
    def parse(self):
        try:
            parser = HTMLTableParser()
            parser.parse_soup(self.soup)
            self._remove_reference(self.soup)
            # convert an html table into a grid without merged cells
            self.unmerged_table = parser.get_columns()
        except Exception as e:
            self.log.warn(e)
            self.log.warn("HTMLTableParser: unable to parse raw html table.")
            return False
        try:
            self.headers, row_idx = self._parse_headers()
        except Exception as e:
            self.log.warn(e)
            self.log.warn("Unable to parse header.")
            return False
        try:
            self.columns = self._parse_data(row_idx)
        except Exception as e:
            self.log.warn(e)
            self.log.warn("Unable to parse data.")
            return False
        
        if not all(len(self.columns[0]) == len(col) for col in self.columns):
            self.log.warn("Columns don't have the same number of entries. Expect {}".format(len(self.columns[0])))
            return False

        # remove the summary rows
        self._remove_summary_rows()

        self.log.debug(self.string_headers())
        self.log.debug(self.columns)

        # add only non-empty columns
        mapping = {}
        for i, h in enumerate(self.string_headers()):
            if not self._is_empty_list(self.columns[i]):
                mapping[h] = self.columns[i]

        nattr = len(mapping)

        # convert into a dataframe
        self.dataframe = pd.DataFrame(mapping)
        self.dataframe.infer_objects()

        if self.dataframe.empty:
            self.isvalid = False
            return False

        self.isvalid = True
        return True
    
    # returns a list of headers as a list of strings
    def string_headers(self):
        if self.string_headers_type == self.JOIN:
            return [":".join(header) for header in self.headers]
        return [header[-1] for header in self.headers]

    # returns the number of rows
    def count_rows(self):
        return len(self.columns[0])
    
    # returns the number of columns
    def count_cols(self):
        return len(self.columns)
    
    # get specific row by index
    def get_row(self, i):
        row = [self.columns[j][i] for j in range(self.count_cols())]
        return row

    # iterate over rows
    def iter_row(self):
        for i in range(self.count_rows()):
            yield self.get_row(i)
    
    # implement iteratorr
    def __iter__(self):
        return self.iter_row()

    # the string representation of this object
    def __str__(self):
        if not self.isvalid:
            return "INVALID TABLE"
        return str(self.dataframe)


# a class for table name generation
class TableNameFactory:

    def __init__(self):
        self.counter = 0
    
    def get_name(self):
        name = 'table_{0:05d}'.format(self.counter)
        self.counter += 1
        return name

# a class for parsing all tables in a wikipedia page
class WikiPage:

    def __init__(self, url, log):
        self.url = url
        self.tables = []
        self.log = log
        self.table_name_factory = TableNameFactory()
    
    # get table's name, not implemented
    def _get_table_name(self, table):
        return None

    # parse all tables in a Wikipedia page
    def parse_tables(self):
        self.log.info("GET " + self.url)
        r = requests.get(self.url)
        self.log.info("Response: {}".format(r.status_code))
        soup = BS(r.content, features="html.parser", from_encoding='utf-8')
        tables = soup.findAll("table", attrs={"class": "wikitable"})
        self.log.info("{} table(s) found.".format(len(tables)))
        nvalid = 0
        for i, t in enumerate(tables):
            self.log.info("Parsing table {}/{}...".format(i+1, len(tables)))
            table_name = self._get_table_name(t) or self.table_name_factory.get_name()
            wtable = WikiTable(t, self.log, name=table_name)
            wtable.parse()
            if wtable.isvalid:
                nvalid += 1
                self.tables.append(wtable)
                self.log.info("=== TABLE ({}/{}) ===".format(i+1, len(tables)))
                self.log.info("Number of attributes: {}".format(wtable.count_cols()))
                self.log.info("Number of rows: {}".format(wtable.count_rows()))
                self.log.info("\n{}".format(str(wtable)))
                self.log.info("\n{}".format(str(wtable.dataframe.dtypes)))
                self.log.info("=== END OF TABLE ===")
        self.log.info("{}/{} tables are valid.".format(nvalid, len(tables)))
    
    # save the tables as csv files
    def save(self, outpath='.'):
        for i, wtable in enumerate(self.tables):
            self.log.debug("mkdir -p {}".format(outpath))
            os.makedirs(outpath, exist_ok=True)
            fp = os.path.join(outpath, wtable.name + '.csv'.format(i))
            self.log.info("Write to file {}".format(fp))
            wtable.dataframe.to_csv(fp, index=False)

if __name__ == "__main__":

    pass
