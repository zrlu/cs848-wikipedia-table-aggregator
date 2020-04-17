# Wikipedia Table Aggregator
## Setup
The software supports Python 3.6.9

Install the required Python modules:
##
```python
pip3 install -r requirements.txt
```

## General Usage

### 1. Download tables from Wikipedia

#### Option 1: give a list of wikipedia links

```
python3 get_tables.py url \
https://en.wikipedia.org/wiki/Michael_Jordan \
https://en.wikipedia.org/wiki/Kobe_Bryant
```

#### Option 2: from a .sparql file

The SPARQL query must return a list of URLs of Wikipedia pages.
```
python3 get_tables.py sparql nba.sparql 
```

The tables will be located in `wiki/` folder. 

For more options: `python3 get_tables.py -h`. 

### 2. Get aggregation result

Run the command prompt program, type `h` for help.
```python
python3 agg.py
# get a list of column names
>> show_info()
# (displays columns and data type)

# peek values in a column
peek('3P%')

# peek values in a column and ignore nan
peek('3P%', dropna=True)

# compute the average
>> agg('mean', 'field_goals')
0.5460839705028452

# you can change the column name mapping in rules.py, then reload everything
>> load()
1558 csv file(s) loaded.
True

# accessing the concatenated dataframe
>> type(cat)
"<class 'pandas.core.frame.DataFrame'>"

# accessing a single column
>> cat['3P%']
0    0.324
1    0.361
2     0.26
0    0.324
1    0.368
     ...  
0        0
1    0.318
2    0.333
3    0.167
4    0.263
Name: 3P%, Length: 9131, dtype: object

# manipulate the dataframe directy
# find all 3P% where Year starts with "2009" or Year is 2009
pd.to_numeric(cat[cat['Year'].str.match("2009") | (cat['Year'] == 2009)]['3P%'], errors='coerce')

```