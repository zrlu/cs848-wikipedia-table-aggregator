# -*- coding: utf-8 -*-

import pdb

class HTMLTableParser:

    def __init__(self):
        self.downward_growing_cells = []
        self.table_info = []

    def _process_table_info_row(self, rowidx, row):
        if len(self.downward_growing_cells) == 0:
            for cell in row:
                colspan, rowspan, soup = cell
                for _ in range(colspan):
                    self.downward_growing_cells.append([(0, rowspan, soup)])
        else:
            colidx = 0
            while colidx < len(self.downward_growing_cells):
                col = self.downward_growing_cells[colidx]
                start_rowidx, rowspan, soup = col[-1]
                if rowidx < start_rowidx + rowspan or rowspan == 0:
                    col.append(col[-1])
                    colidx += 1
                else:
                    cell = row.pop(0)
                    colspan, rowspan, soup = cell
                    for _ in range(colspan):
                        self.downward_growing_cells[colidx].append((rowidx, rowspan, soup))
                        colidx += 1

    def parse_soup(self, soup):

            tbody = soup.find('tbody')
            for tr in tbody.find_all('tr', class_='sortbottom'):
                tr.decompose()

            for rowidx, tr in enumerate(tbody.find_all('tr', recursive=False)):
                table_row_info = []
                for cellidx, cell in enumerate(tr.find_all(['th', 'td'], recursive=False)):
                    colspan = int(cell.get('colspan', '1'))
                    rowspan = int(cell.get('rowspan', '1'))
                    table_row_info.append((colspan, rowspan, cell))
                self.table_info.append(table_row_info)

            for rowidx, row in enumerate(self.table_info):
                self._process_table_info_row(rowidx, row)
    
    def print(self):
            from prettytable import PrettyTable
            pt = PrettyTable()
            for i in range(len(self.downward_growing_cells[0])):
                row = []
                for col in self.downward_growing_cells:
                    start, rowspan, soup = col[i]
                    row.append(soup.text.strip())
                pt.add_row(row)
            print(str(pt))

    def get_columns(self):
        return [[tup[2] for tup in col] for col in self.downward_growing_cells]

if __name__ == '__main__':
    import sys, io
    from prettytable import PrettyTable
    from bs4 import BeautifulSoup as BS

    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

    with open('unmergetest.html', 'r', encoding='utf-8') as file:
        parser = HTMLTableParser()
        soup = BS(file.read(), features='html.parser', from_encoding='utf-8')
        parser.parse_soup(soup)
        parser.print()