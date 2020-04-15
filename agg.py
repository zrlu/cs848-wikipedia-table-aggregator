from wikitable import WikiPage
import pandas as pd
from glob import glob
import pdb
from rules import column_mapper

def load(path='wiki/'):
    global cat
    dataframes = []
    csv_path_list = glob(path + '/**/*.csv', recursive=True)
    for csv in csv_path_list:
        df = pd.read_csv(csv)
        df.rename(columns=column_mapper, inplace=True)
        dataframes.append(df)
    cat = pd.concat(dataframes)
    print('{} csv file(s) loaded.'.format(len(csv_path_list)))
    return True

def show_info():
    cat.info(verbose=True)

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
    print('q: exit')
    print('h: display this message')
    print('VARIABLES:')
    print('cat: access the concatenated dataframe of wikipedia tables')
    print('PYTHON FUNCTIONS:')
    print('show_info(): show the columns of the dataframe, run once when this programs starts')
    print("load(path=\'wiki\\\'): load csv files into a concatenated dataframe, run once when this program starts")

if __name__ == '__main__':
  
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
