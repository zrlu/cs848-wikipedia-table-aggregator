# -*- coding: utf-8 -*-
 
import pandas as pd
from glob import glob
import pdb
import rules
from importlib import reload

def load(path='wiki/'):
    global cat
    reload(rules)
    dataframes = []
    csv_path_list = glob(path + '/**/*.csv', recursive=True)
    for csv in csv_path_list:
        df = pd.read_csv(csv)
        df.rename(columns=rules.column_mapper, inplace=True)
        dataframes.append(df)
    cat = pd.concat(dataframes)
    print('{} csv file(s) loaded.'.format(len(csv_path_list)))
    return True

def show_info():
    cat.info(verbose=True)

def peek(col_name, dropna=False):
    if dropna:
        print(cat[col_name].dropna())
    else:
        print(cat[col_name])

def agg(agg, col_name):
    col = pd.to_numeric(cat[col_name], errors='coerce')

    if agg in ['mean', 'avg', 'average', 'ave']:
        return col.mean()
    if agg in ['min', 'minimum']:
        return col.min()
    if agg in ['max', 'maximum']:
        return col.max()
    if agg in ['sum']:
        return col.sum()
    if agg in ['count', 'size']:
        return col.count()
    return None

def help():
    print('COMMANDS:')
    print('\t', 'q: exit')
    print('\t', 'h: display this message')
    print('VARIABLES:')
    print('\t', 'cat: access the concatenated dataframe of wikipedia tables')
    print('PYTHON FUNCTIONS:')
    print('\t', 'show_info(): show the column information of the concatenated dataframe, run once when this programs starts')
    print('\t', "load(path): reload csv files under path into a concatenated dataframe and the column name mapping rules, run once when this program starts, default path is 'wiki'")
    print('\t', "agg(type, column): aggregate the column. type is in ['max', 'min', 'count', 'sum', 'mean'] ")
    print('\t', "peek(column, dropna=False): peek values in a column, ignore NaN by setting dropna=True")

if __name__ == '__main__':
  
    print('loading the csv files...')
    load()
    show_info()

    print('type \'h\' to display help message')

    while True:
        try:
            expr = input(">> ")
            if expr in ['q', 'quit', 'exit']:
                print('bye!')
                break
            if expr in ['h', 'help']:
                help()
                continue
            ret = eval(expr)
            print(ret)
        except SyntaxError:
            continue
        except KeyboardInterrupt:
            break
        except EOFError:
            break
        except Exception as e:
            print(e)
            continue
