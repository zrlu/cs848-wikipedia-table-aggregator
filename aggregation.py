from wikitable import WikiPage
import pandas as pd
from glob import glob
import pdb
from rules import column_mapper

def load(path):
    global cat
    dataframes = []
    csv_path_list = glob(path + '/*/*.csv')
    for csv in csv_path_list:
        df = pd.read_csv(csv)
        df.rename(columns=column_mapper, inplace=True)
        dataframes.append(df)
    cat = pd.concat(dataframes)

def show_info():
    cat.info(verbose=True)

def agg(agg, col_name):
    col = pd.to_numeric(cat[col_name], errors='coerce')

    if agg == 'mean' or agg == 'avg' or agg == 'average':
        return col.mean()
    if agg == 'min' or agg == 'minimum':
        return col.min()
    if agg == 'max' or agg == 'maximum':
        return col.max()
    if agg == 'sum':
        return col.sum()
    if agg == 'count' or agg == 'size':
        return col.count()
    return None

if __name__ == '__main__':
  
    load('wiki/')
    show_info()

    pdb.set_trace()
