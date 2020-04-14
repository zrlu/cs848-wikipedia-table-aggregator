from wikitable import WikiPage
import pandas as pd
from glob import glob
import pdb

if __name__ == '__main__':
    dataframes = []
    csv_path_list = glob('wiki/*/*.csv')
    for csv in csv_path_list:
        print(csv)
        df = pd.read_csv(csv)
        dataframes.append(df)
    pdb.set_trace()