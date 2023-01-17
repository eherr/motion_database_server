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
SKELETON_TABLE = [("name",TEXT_T),
                    ("data",BLOB_T), 
                    ("metaData",BLOB_T),
                    ("owner",TEXT_T)]
MOTION_TABLE = [("name",TEXT_T),
                    ("collection",INT_T), 
                    ("skeleton",INT_T), 
                    ("data",BLOB_T), 
                    ("metaData",BLOB_T), 
                    ("subject",TEXT_T), 
                    ("numFrames",INT_T),  
                    ("source",TEXT_T)]
DATA_TABLE = [("name",TEXT_T),
                    ("collection",INT_T), 
                    ("skeleton",INT_T), 
                    ("data",BLOB_T), 
                    ("metaData",BLOB_T),
                    ("numFrames",INT_T),  
                    ("source",TEXT_T)]
MODELS_TABLE = [("name",TEXT_T),
            ("collection",INT_T), 
            ("skeleton",INT_T), 
            ("data",BLOB_T), 
            ("metaData",BLOB_T)]
GRAPH_TABLE = [("name",TEXT_T),
                ("skeleton",INT_T), 
                ("data",BLOB_T)]
USER_TABLE = [("name",TEXT_T),
    ("password",TEXT_T), 
    ("role",TEXT_T), 
    ("sharedAccessGroups",TEXT_T), 
    ("email",TEXT_T)]
USER_GROUPS_TABLE = [("name",TEXT_T), # need to be unique
            ("owner",INT_T),     # user id
            ("users",TEXT_T)]   #  list of user ids 
EXPERIMENTS_TABLE = [("name",TEXT_T), # need to be unique
                    ("collection",INT_T), 
                    ("skeleton",INT_T),  
                    ("owner",INT_T),     # user id 
                    ("codeURL",TEXT_T),   
                    ("cmd",TEXT_T),   
                    ("hyperparameters",TEXT_T), 
                    ("imageURL",TEXT_T),    
                    ("resourceConfig",TEXT_T),   
                    ("logURL",TEXT_T)] 
TABLES2 = dict()
TABLES2["collections"] = COLLECT_TABLE
TABLES2["skeletons"] = SKELETON_TABLE
TABLES2["motion_clips"] = MOTION_TABLE
TABLES2["preprocessed_data"] = DATA_TABLE
TABLES2["models"] = MODELS_TABLE
TABLES2["graphs"] = GRAPH_TABLE
TABLES2["users"] = USER_TABLE
TABLES2["user_groups"] = USER_GROUPS_TABLE
TABLES2["experiments"] = EXPERIMENTS_TABLE





TABLES3 = dict()
TABLES3["collections"] = COLLECT_TABLE
TABLES3["skeletons"] = [("name",TEXT_T),
                    ("data",TEXT_T), 
                    ("metaData",TEXT_T),
                    ("owner",TEXT_T)
                    ]
TABLES3["motion_clips"] = [("name",TEXT_T),
                    ("collection",INT_T), 
                    ("skeleton",INT_T), 
                    ("data",TEXT_T), 
                    ("metaData",TEXT_T), 
                    ("subject",TEXT_T),
                    ("numFrames",INT_T), 
                    ("format",TEXT_T), 
                    ("source",TEXT_T)]
TABLES3["preprocessed_data"] = [("name",TEXT_T),
                    ("collection",INT_T), 
                    ("skeleton",INT_T), 
                    ("data",TEXT_T), 
                    ("metaData",TEXT_T), 
                    ("numFrames",INT_T), 
                    ("format",TEXT_T), 
                    ("source",TEXT_T)]
TABLES3["models"] = [("name",TEXT_T),
                    ("collection",INT_T), 
                    ("skeleton",INT_T), 
                    ("data",TEXT_T), 
                    ("metaData",TEXT_T)]
TABLES3["graphs"] = [("name",TEXT_T),
                    ("skeleton",INT_T), 
                    ("data",TEXT_T)]
TABLES3["users"] = USER_TABLE
TABLES3["user_groups"] = USER_GROUPS_TABLE
TABLES3["experiments"] = EXPERIMENTS_TABLE
TABLES3["meshes"] = [("name",TEXT_T), 
                    ("skeleton",INT_T),
                    ("data",TEXT_T)]


DATA_COLS = ["data", "metaData"]

class DBSchema:
    def __init__(self, tables):
        self.tables = tables

    def get_data_cols(self, table_name):
        return [k for k in DATA_COLS if k in self.tables[table_name]]

    def create_tables(self, db):
        for t_name in self.tables:
            db.create_table(t_name, self.tables[t_name], replace=True)
        