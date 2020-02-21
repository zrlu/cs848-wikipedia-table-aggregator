import requests
from bs4 import BeautifulSoup as BS
import pprint
import sys
import io
import operator
from collections import UserList
import logging
from prettytable import PrettyTable

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

class WikiTable:
    
    def __init__(self, soup, logging):
        self.soup = soup
        self.title = None
        self.headers = []
        self.columns = []
        self.ndata = 0
        self.nattr = 0
        self.isvalid = False
        self.logging = logging
    
    def extract_cell(self, element):
        # remove citations
        sup = element.find("sup")
        if sup:
            sup.decompose()
        return element.text.strip()

    def parse_headers(self):
        entries = []
        trs = self.soup.find_all('tr')
        nrow = 0
        nattr = 0
        for row in trs:
            rows = []
            ths = row.find_all('th')
            ncol = 0
            for th in ths:
                text = self.extract_cell(th)
                colspan = int(th.get("colspan", "1"))
                rowspan = int(th.get("rowspan", "1"))
                for ci in range(ncol, ncol + colspan):
                    for ri in range(nrow, nrow + rowspan):
                        entries.append((ri, ci, text))
                ncol += colspan
                nattr = max(nattr, ncol)
            nrow += 1
            if (rows):
                entries.append(rows)

        entries.sort(key=operator.itemgetter(0, 1))

        n = len(entries) // nattr
        headers = [[] for i in range(nattr)]

        for i in range(n):
            for j in range(nattr):
                entry = entries[i*nattr+j]
                colname = entry[2]
                if headers[j] == [] or headers[j][-1] != colname:
                    headers[j].append(colname)
        return headers
 
    def parse_data(self):
        entries = []
        trs = self.soup.find_all('tr')
        nrow = 0
        nattr = 0
        for row in trs:
            rows = []
            tds = row.find_all('td')
            ncol = 0
            for td in tds:
                text = td.text.strip()
                colspan = int(td.get("colspan", "1"))
                rowspan = int(td.get("rowspan", "1"))
                for ci in range(ncol, ncol + colspan):
                    for ri in range(nrow, nrow + rowspan):
                        entries.append((ri, ci, text))
                ncol += colspan
                nattr = max(nattr, ncol)
            nrow += 1
            if (rows):
                entries.append(rows)
        
        entries.sort(key=operator.itemgetter(0, 1))
        n = len(entries) // nattr
        columns = [[] for i in range(nattr)]

        for i in range(n):
            for j in range(nattr):
                entry = entries[i*nattr+j]
                value = entry[2]
                columns[j].append(value)
        return columns

    def parse(self):
        try:
            self.headers = self.parse_headers()
        except Exception as e:
            self.logging.error(e)
            self.logging.error("Unable to parse header.")
            return False
        try:
            self.columns = self.parse_data()
        except Exception as e:
            self.logging.error(e)
            self.logging.error("Unable to parse data.")
            return False
        nattr = len(self.headers)
        if nattr != len(self.columns):
            self.logging.error("The number of attributes does not match with the number of columns.")
            return False
        if not all(len(self.columns[0]) == len(col) for col in self.columns):
            self.logging.error("Columns don't have the same number of entries. Expect {}".format(len(self.columns[0])))
            return False
        self.nattr = nattr
        self.ndata = len(self.columns[0])
        self.isvalid = True
        return True
    
    def __str__(self):
        if not self.isvalid:
            return "INVALID TABLE"
        pt = PrettyTable([":".join(header) for header in self.headers])
        for i in range(self.ndata):
            row = [self.columns[j][i] for j in range(self.nattr)]
            pt.add_row(row)
        return str(pt)

# r = requests.get("https://en.wikipedia.org/wiki/2010%E2%80%9311_Premier_League");
#soup = BS(r.content)
#tables = soup.findAll("table")

with open("table2.html", "r", encoding="utf-8") as f:
    test_html = f.read()
    test_table = BS(test_html, features="html.parser")
    wtable = WikiTable(test_table, logging)
    wtable.parse()
    print(wtable)