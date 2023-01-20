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

DATA_COLS = ["data", "metaData"]

"""
Table interface that stores certain columns in the filesystem
The database only has to store the filename.
The filename is generated based on the hash and the date
"""
class Table():
    def __init__(self, db, table_name, columns, data_cols=DATA_COLS) -> None:
        self.table_name = table_name
        self.cols = [c[0] for c in columns]
        self.data_cols = [c for c in self.cols if c in data_cols]
        self.db = db

    def search_records_by_name(self, name, cols=None, exact_match=False, filter_conditions=[]):
        if cols is None:
            cols = self.cols
        filter_conditions += [("name", name, exact_match)]
        records = self.db.query_table(self.table_name, cols, filter_conditions, None)
        data_col_idx = [i for i, c in enumerate(cols) if c in self.data_cols]
        if len(data_col_idx) > 0:
            for i, r in enumerate(records):
                records[i] = self.read_data_columns(r, data_col_idx)
        return records
    
    def get_record_by_name(self, entry_name, cols=None):
        if cols is None:
            cols = self.cols
        filter_conditions =  [("name", entry_name)]
        records = self.db.query_table(self.table_name, cols,filter_conditions)
        record = None
        if len(records) > 0:
            record = list(records[0])
            col_idx = [i for i, c in enumerate(cols) if c in self.data_cols]
            record = self.read_data_columns(record, col_idx)
        return record

    def get_record_by_id(self, entry_id, cols=None):
        if cols is None:
            cols = self.cols
        filter_conditions =  [("ID", entry_id)]
        records = self.db.query_table(self.table_name, cols,filter_conditions)
        record = None
        if len(records) > 0:
            record = list(records[0])
            col_idx = [i for i, c in enumerate(cols) if c in self.data_cols]
            record = self.read_data_columns(record, col_idx)
        return record

    def read_data_columns(self, record, col_idx):
        for i in col_idx:
            print("read", self.table_name, record[i])
            record[i] = self.db.load_data_file(self.table_name, record[i])
        return record

    def write_data_columns(self, input_data):
        modified_data_cols = []
        data = dict()
        for key in self.cols:
            if key in input_data:
                if key in self.data_cols:
                    filename = self.db.save_hashed_file(self.table_name, key, input_data[key])
                    print("write",self.table_name, filename)
                    data[key] = filename
                    modified_data_cols.append(key)
                else:
                    data[key] = input_data[key]
        return data, modified_data_cols

    def update_record(self, entry_id, input_data):
        data, modified_data_cols = self.write_data_columns(input_data)
        if len(modified_data_cols) > 0:
            self.delete_files_of_record([("ID",entry_id)], modified_data_cols)
        self.db.update_entry(self.table_name, data, "ID", entry_id)

    def update_record_by_name(self, entry_name, input_data):
        data, modified_data_cols = self.write_data_columns(input_data)
        if len(modified_data_cols) > 0:
            self.delete_files_of_record([("name",entry_name)], modified_data_cols)
        self.db.update_entry(self.table_name, data, "name", entry_name)

    def create_record(self, input_data):
        input_data, modified_data_cols = self.write_data_columns(input_data)
        col_keys = []
        cols_values = []
        for key in input_data:
            col_keys.append(key)
            cols_values.append(input_data[key])
        records = [cols_values]
        self.db.insert_records(self.table_name, col_keys, records)
        records = self.db.get_max_id(self.table_name)
        new_id = -1
        if len(records) > 0:
            new_id = int(records.iloc[0]["ID"])
        return new_id

    def get_record_list(self, cols=None, filter_conditions=[],intersection_list=[], load_data_files=True, join_statement=None, distinct=False):
        if cols is None:
            cols = self.cols
        records = self.db.query_table(self.table_name, cols, filter_conditions,intersection_list,join_statement, distinct)
        if load_data_files:
            data_col_idx = [i for i, c in enumerate(cols) if c in self.data_cols]
            if len(data_col_idx) > 0:
                for i, r in enumerate(records):
                    records[i] = self.read_data_columns(list(r), data_col_idx)
        return records

    def get_value_of_column_by_id(self, entry_id, col_name):
        value = None
        record = self.get_record_by_id(entry_id, [col_name])
        if record is not None:
            value = record[0]
        return value

    def get_value_of_column_by_name(self, entry_name, col_name):
        value = None
        record = self.get_record_by_name(entry_name, [col_name])
        if record is not None:
            value = record[0]
        return value

    def get_data_cols(self):
        return self.data_cols

    def delete_record_by_id(self, entry_id):
        filter_conditions = [("ID",entry_id)]
        if len(self.data_cols) > 0:
            self.delete_files_of_record(filter_conditions, self.data_cols)
        self.db.delete_entry_by_id(self.table_name, entry_id)

    def delete_record_by_name(self, entry_name):
        filter_conditions = [("name",entry_name)]
        if len(self.data_cols) > 0:
            self.delete_files_of_record(filter_conditions, self.data_cols)
        self.db.delete_entry_by_name(self.table_name, entry_name)

    def delete_record_by_condition(self, filter_conditions):
        if len(self.data_cols) > 0:
            self.delete_files_of_record(filter_conditions, self.data_cols)
        self.db.delete_entry_by_condition(self.table_name, filter_conditions)
        
    def delete_files_of_record(self, filter_conditions, data_cols):
        data_records = self.get_record_list(data_cols, filter_conditions, load_data_files=False)
        if len(data_records) <1:
            return
        for data_file_name in data_records[0]:
            print("delete file", self.table_name, data_file_name)
            self.db.delete_data_file(self.table_name, data_file_name)
