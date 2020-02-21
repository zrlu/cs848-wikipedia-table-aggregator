import requests
from bs4 import BeautifulSoup as BS
import pprint
import sys
import io
import operator
from collections import UserList
import logging
from prettytable import PrettyTable
import argparse

class WikiTable:
    
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
    
    def extract_header_cell(self, element):
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
        text = element.text.strip()
        try:
            num = int(text.replace(",", ""))
            return num
        except ValueError:
            pass
        try:
            num = float(text.replace(",", ""))
            return num
        except ValueError:
            pass
        return text

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
                text = self.extract_header_cell(th)
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
                text = self.extract_data_cell(td)
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
            self.log.warn(e)
            self.log.warn("Unable to parse header.")
            return False
        try:
            self.columns = self.parse_data()
        except Exception as e:
            self.log.warn(e)
            self.log.warn("Unable to parse data.")
            return False
        nattr = len(self.headers)
        if nattr == 1:
            self.log.warn("Discarding tables with only 1 column.")
            self.isvalid = False
            return False
        if nattr != len(self.columns):
            self.log.warn("The number of attributes does not match with the number of columns.")
            self.log.warn("The number of attributes is {}".format(nattr))
            self.log.warn("The number of columns is {}".format(len(self.columns)))
            self.log.debug("Headers: ")
            self.log.debug(self.headers)
            return False
        if not all(len(self.columns[0]) == len(col) for col in self.columns):
            self.log.warn("Columns don't have the same number of entries. Expect {}".format(len(self.columns[0])))
            return False
        unique_headers = set()
        string_headers = [":".join(header) for header in self.headers]
        for header in string_headers:
            if header not in unique_headers:
                unique_headers.add(header)
            else:
                self.log.warn("Duplicate header '{}' found.".format(header))
                return
        self.string_headers = string_headers
        self.nattr = nattr
        self.ndata = len(self.columns[0])
        self.isvalid = True
        return True
    
    def __str__(self):
        if not self.isvalid:
            return "INVALID TABLE"
        pt = PrettyTable(self.string_headers)
        for i in range(self.ndata):
            row = [self.columns[j][i] for j in range(self.nattr)]
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
    formatter = logging.Formatter('%(asctime)s %(levelname)-8s [%(filename)s:%(lineno)d] %(message)s')
    fileHandler = logging.FileHandler('job.log', 'w', 'utf-8')
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
                if (args.show):
                    log.info("Table ({}/{})\n{}".format(i+1, len(tables), str(wtable)))
        log.info("{}/{} tables are valid.".format(nvalid, len(tables)))