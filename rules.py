# -*- coding: utf-8 -*-

summary_row_keywords = "sum|average|total|turnout|majority|summary|career|all-star"
cell_remove_special_symbols = "\*|†|~|\u200d"
cell_replace_special_symbols = [("\u2010|\u2011|\u2012|\u2013|\u2014|\u2015", '-'), ('\xa0', ' ')]
column_mapper = {
    'FG%': 'field_goals',
    'Field Goals': 'field_goals'
}