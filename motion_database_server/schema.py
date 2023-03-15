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

INT_T = "INTERGER"
BLOB_T = "BLOB"
TEXT_T = "TEXT"

TABLES = dict()
TABLES["collections"] = [("name",TEXT_T),
                    ("type",TEXT_T), 
                    ("owner",INT_T), 
                    ("parent",INT_T)]
TABLES["skeletons"] = [("name",TEXT_T),
                    ("data",BLOB_T), 
                    ("metaData",BLOB_T),
                    ("owner",INT_T)]
TABLES["motion_clips"] = [("name",TEXT_T),
                    ("collection",INT_T), 
                    ("skeletonType",INT_T), 
                    ("quaternionFrames",TEXT_T), 
                    ("metaInfo",TEXT_T)]
TABLES["models"] = [("name",TEXT_T),
                    ("collection",INT_T), 
                    ("skeleton",INT_T), 
                    ("data",BLOB_T), 
                    ("metaData",BLOB_T)]
TABLES["graphs"] = [("name",TEXT_T),
                    ("skeleton",INT_T), 
                    ("data",BLOB_T)]


COLLECT_TABLE = [("name",TEXT_T),
                    ("type",TEXT_T), 
                    ("owner",TEXT_T), 
                    ("parent",INT_T), 
                    ("public",INT_T)]
TABLES = dict()
TABLES["collections"] = COLLECT_TABLE
TABLES["skeletons"] = [("name",TEXT_T),
                    ("data",TEXT_T), 
                    ("metaData",TEXT_T),
                    ("owner",TEXT_T)
                    ]
TABLES["users"] = [("name",TEXT_T),
                    ("password",TEXT_T), 
                    ("role",TEXT_T), 
                    ("email",TEXT_T)]
TABLES["projects"] = [("name",TEXT_T), 
                    ("owner",INT_T),   
                    ("collection",INT_T),   
                    ("public",INT_T)]  
TABLES["project_members"] = [("user",INT_T), ("project",INT_T)] 




TABLES["files"] = [("name",TEXT_T),
                    ("collection",INT_T), 
                    ("skeleton",INT_T), 
                    ("data",TEXT_T), 
                    ("metaData",TEXT_T),
                    ("dataType",TEXT_T),
                    ("numFrames",INT_T),
                    ("comment",TEXT_T),
                    ("subject",TEXT_T),
                    ("source",TEXT_T),
                    ("processed",INT_T)]

TABLES["data_types"] =  [("name",TEXT_T), # need to be unique
                ("requirements",TEXT_T),
                ("isModel",INT_T),
                ("isTimeSeries",INT_T),
                ("isSkeletonMotion",INT_T),
                ("isProcessed",INT_T)
                ]

TABLES["data_loaders"] = [("dataType",TEXT_T),
            ("engine",TEXT_T),
            ("script",INT_T), 
            ("requirements",TEXT_T)]

TABLES["data_transforms"] = [("name",TEXT_T),
            ("script",TEXT_T),
            ("parameters",TEXT_T),
            ("requirements",TEXT_T),
            ("outputIsCollection",INT_T),
            ("outputType",TEXT_T)]

TABLES["data_transform_inputs"] = [("dataTransform",INT_T),
            ("dataType",TEXT_T),
            ("isCollection",INT_T)]


#experiments are instances of data transforms
TABLES["experiments"] = [("name",TEXT_T), # need to be unique
                    ("collection",INT_T), 
                    ("skeleton",INT_T), 
                    ("dataTransform",INT_T),
                    ("config",TEXT_T),   
                    ("logFile",TEXT_T),
                    ("logFields",TEXT_T),
                    ("externalURL",TEXT_T),  
                    ("owner", INT_T),
                    ("output",INT_T) # can be collection or file
                    ] 
TABLES["experiment_inputs"] = [
            ("dataTransformInput",INT_T),
            ("experiment",INT_T),
            ("input",INT_T)]

TABLES["tags"] =  [("name",TEXT_T), # need to be unique
                ]

TABLES["data_type_taggings"] =  [("tag",TEXT_T), # need to be unique
                                 ("dataType",TEXT_T)]


TABLES["model_graphs"] = [("name",TEXT_T),
                    ("project",INT_T), 
                    ("skeleton",INT_T), 
                    ("data",TEXT_T)]
TABLES["tags"] = [
            ("name",INT_T)]
TABLES["data_type_taggings"] = [
            ("dataType",TEXT_T),
            ("tag",INT_T)]
import sqlite3

class DBSchema:
    def __init__(self, tables):
        self.tables = tables

    def create_database(self, path):
        con = sqlite3.connect(path)
        for t_name in self.tables:
            self.create_table(con, t_name, self.tables[t_name])
        con.close()

    def create_table(self, con, table_name, columns):
        col_string = ''' (ID INTEGER PRIMARY KEY, '''
        for c_name, c_type in columns:
            col_string += "'"+c_name+"' "+c_type+"," 
        col_string += '''  timestamp DATETIME DEFAULT CURRENT_TIMESTAMP);'''
        con.execute('''CREATE TABLE '''+table_name+col_string)
        con.commit()
