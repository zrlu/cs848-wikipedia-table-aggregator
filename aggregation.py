from wikitable import WikiPage
import pandas as pd
from glob import glob
import pdb
from rules import column_mapper

if __name__ == '__main__':
    dataframes = []
    csv_path_list = glob('wiki2/*/*.csv')
    for csv in csv_path_list:
        df = pd.read_csv(csv)
        df.rename(columns=column_mapper, inplace=True)
        dataframes.append(df)
    concat = pd.concat(dataframes)
    lst = concat['3P%']
    a = [x for x in lst if type(x) == str]
    pdb.set_trace()
