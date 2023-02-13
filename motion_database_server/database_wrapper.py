#!/usr/bin/env python
#
# Copyright 2019 DFKI GmbH.
#
# Permission is hereby granted, free of charge, to any person obtaining a
# copy of this software and associated documentation files (the
# "Software"), to deal in the Software without restriction, including
# without limitation the rights to use, copy, modify, merge, publish,
# distribute, sublicense, and/or sell copies of the Software, and to permit
# persons to whom the Software is furnished to do so, subject to the
# following conditions:
#
# The above copyright notice and this permission notice shall be included
# in all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS
# OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF
# MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN
# NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM,
# DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR
# OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE
# USE OR OTHER DEALINGS IN THE SOFTWARE.
"""
Sources:
http://www.datacarpentry.org/python-ecology-lesson/08-working-with-sql
http://pandas.pydata.org/pandas-docs/stable/dsintro.html
http://pandas.pydata.org/pandas-docs/stable/generated/pandas.DataFrame.to_sql.html
http://stackoverflow.com/questions/36028759/how-to-open-and-convert-sqlite-database-to-pandas-dataframe
http://stackoverflow.com/questions/23574614/appending-pandas-dataframe-to-sqlite-table-by-primary-key
http://www.sqlitetutorial.net/sqlite-python/delete/
"""
import sqlite3
import pandas as pd


class DatabaseWrapper(object):
    def __init__(self):
        self.con = None

    def connect_to_database(self, path):
        self.con = sqlite3.connect(path)
        print("connected to db",path)

    def create_table(self,table_name, columns, replace=False):
        if replace:
            self.con.execute(''' DROP TABLE IF EXISTS '''+table_name+''';''')
        col_string = ''' (ID INTEGER PRIMARY KEY, '''
        for c_name, c_type in columns:
            col_string += "'"+c_name+"' "+c_type+"," 
        col_string += '''  timestamp DATETIME DEFAULT CURRENT_TIMESTAMP);'''
        self.con.execute('''CREATE TABLE '''+table_name+col_string)
        self.con.commit()

    def write_pd(self, table_name, data):
        print("write pandas data to sql table", table_name)
        data.to_sql(table_name, self.con, if_exists="replace")

    def get_column_names(self, table_name):
        query_str = "PRAGMA table_info(" + table_name + ");"
        query = self.con.execute(query_str)
        result = query.fetchall()
        return [r[1] for r in result[1:]]

    def close(self):
        self.con.close()
        print("closed connection to db")

    def read_pd(self, table_name):
        print("read pandas data from sql table", table_name)
        query_str = "SELECT * From " + table_name
        results = pd.read_sql_query(query_str, self.con)
        return results
        
    def update_entry(self,  table_name, data, condition_key, condition_value):
        query_str = ''' UPDATE '''+table_name+''' SET ''' 
        n_entries = len(data)
        count = 0
        values = []
        for key, value in data.items():
            query_str += key  + '''= ?'''
            count+=1
            values.append(value)
            if n_entries > count:
                query_str +=''', '''
        query_str +=  ''' WHERE '''+ condition_key +'''= ?;'''
        values.append(condition_value)
        cur = self.con.cursor()
        cur.execute(query_str, tuple(values))
        self.con.commit()

    def update_entry_by_condition(self, table_name, data, conditions):
        query_str = ''' UPDATE '''+table_name+''' SET ''' 
        n_entries = len(data)
        count = 0
        for key, value in data.items():
            query_str +=self.get_filter_str((key, value))
            count+=1
            if n_entries > count:
                query_str +=", "
        query_str += self.get_condition_str(conditions, None)
        query_str +=  ";"
        cur = self.con.cursor()
        cur.execute(query_str)
        self.con.commit()

    def get_max_id(self, table):
        query_str = "SELECT max(ID) as ID FROM " + table + " ;"
        return pd.read_sql_query(query_str, self.con)

    def insert_records(self, table, columns, records):
        if len(records) < 1:
            print("Error: No records to insert")

            return
        if len(columns) != len(records[0]):
            print("Error: Column names list and record column length do not match",len(columns), len(records[0]))
            return

        query_str = " INSERT INTO " + table + " ( "
        for idx, c in enumerate(columns):
            if idx > 0:
                query_str += ","
            query_str += c + " "
        query_str += ") VALUES ("
        for idx, c in enumerate(columns):
            if idx > 0:
                query_str += ","
            query_str += "?"
        query_str += ")"
        print(query_str)
        self.con.executemany(query_str, records)
        self.con.commit()

    def get_records(self, table, columns, group=None, q_filter=None, order=None):
        query_str = "SELECT "
        if group is not None:
            query_str += "Max(Timestamp),"
        for idx, c in enumerate(columns):
            if idx > 0:
                query_str += ", "
            query_str += c

        query_str +=" From " + table
        if q_filter is not None:
            query_str += " WHERE "
            for idx, c in enumerate(q_filter):
                if idx > 0:
                    query_str += " AND "
                query_str += c[0]+" = "+c[1]

        if group is not None:
            query_str += " GROUP BY "
            for idx, c in enumerate(group):
                if idx > 0:
                    query_str += ","
                query_str += " " + c
        if order is not None:
            query_str += " ORDER BY "
            for idx, c in enumerate(order):
                if idx > 0:
                    query_str += ","
                query_str += " " + c

        query_str += ";"
        return pd.read_sql_query(query_str, self.con)

    def get_filter_str(self, c):
        query_str = ""
        if type(c[1]) == str:
            if len(c) > 2 and not c[2]: # allow partial match
                query_str = c[0]+" LIKE '%"+c[1]+"%'"
            else:
                query_str = c[0]+" = '"+c[1]+"'"
        elif type(c[1]) == list:
            list_str = "".join(["'"+str(v)+"', " for v in c[1][:-1]])
            list_str = "(" + list_str
            list_str +=  str(c[1][-1]) + ")"
            query_str = c[0]+" IN " + list_str
        else:
            query_str = c[0]+" = "+str(c[1])
        return query_str

    def get_condition_str(self, filter_list=None, intersection_list=None):
        query_str = ""
        has_filter_list = filter_list is not None and len(filter_list) > 0
        has_intersection_list = intersection_list is not None and len(intersection_list) > 0
        if has_filter_list or has_intersection_list:
            query_str += " WHERE "
        if has_filter_list:
            for idx, c in enumerate(filter_list):
                if idx > 0:
                    query_str += " AND "
                query_str += self.get_filter_str(c)
        if has_intersection_list:
            if has_filter_list:
                query_str += " AND ("
            for idx, c in enumerate(intersection_list):
                if idx > 0:
                    query_str += " OR "
                query_str += self.get_filter_str(c)
            if has_filter_list:
                query_str += ")"
        return query_str

    def query_table(self, table_name, column_list, filter_list=None, intersection_list=None, join_statement=None, distinct=False):
        query_str = "SELECT "
        if distinct:
            query_str += " DISTINCT "
        last_idx = len(column_list)-1
        for idx, c in enumerate(column_list):
            query_str += c
            if idx < last_idx:
                query_str += ", "  
            else:
                query_str += " "  
        query_str += "FROM  " + table_name
        if join_statement is not None:
            query_str += " "+join_statement
        query_str += self.get_condition_str(filter_list, intersection_list)
        query_str += ";"
        #print(query_str)
        records = pd.read_sql_query(query_str, self.con)
        results = []
        for idx, r in records.iterrows():
            record = []
            for k, v in r.items():
                #print(k, v)
                record.append(v)
            results.append(tuple(record))
        return results

    def delete_entry_by_id(self, table_name, motion_id):
        query_str = "DELETE FROM " + table_name + \
                    " WHERE ID="+ str(motion_id) + ";"
        print(query_str)
        self.con.execute(query_str)
        self.con.commit()
    
    def delete_entry_by_name(self, table_name, name):
        query_str = "DELETE FROM " + table_name + \
                    " WHERE name='"+ str(name) + "';"
        print(query_str)
        self.con.execute(query_str)
        self.con.commit()
    
    def delete_entry_by_condition(self, table_name, filter_list=None, intersection_list=None):
        query_str = "DELETE FROM " + table_name
        query_str += self.get_condition_str(filter_list, intersection_list)
        query_str += ";"
        print(query_str)
        self.con.execute(query_str)
        self.con.commit()

    def get_name_list(self, table_name):
        query_str = "SELECT name  FROM " + table_name +" ;"
        results = pd.read_sql_query(query_str, self.con)
        return results
