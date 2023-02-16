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


class CollectionDatabase:
    collections_table = "collections" 
        
    def get_collection_list_by_id(self, parent_id, owner=-1, public=-1):
        filter_conditions =  [("parent",parent_id)]
        intersection_list = []
        if owner >= 0:
            intersection_list.append(("owner",owner))
        if public >= 0:
            intersection_list.append(("public",public))
        return self.tables[self.collections_table].get_record_list(["ID","name","type", "owner", "public"], filter_conditions)
    
    def get_collection_tree(self, parent_id, owner=-1, public=-1):
        col_dict = dict()
        for c in self.get_collection_list_by_id(parent_id, owner, public):
            col_id = c[0]
            col_data = dict()
            col_data["name"] = c[1]
            col_data["type"] = c[2]
            col_data["owner"] = c[3]
            col_data["public"] = c[4]
            col_data["sub_tree"] = self.get_collection_tree(col_id, owner, public)
            col_dict[col_id] = col_data
        return col_dict
      
    def add_new_collection_by_id(self, name, collection_type, parent_id, owner, public=0):
        owner = max(0, owner)
        record_data = dict()
        record_data["name"] = name
        record_data["type"] = collection_type
        record_data["parent"] = parent_id
        record_data["owner"] = owner
        record_data["public"] = public
        return self.tables[self.collections_table].create_record(record_data)

    def remove_collection_by_id(self, collection_id):
        return self.tables[self.collections_table].delete_record_by_id(collection_id)

    def get_owner_of_collection(self, collection_id):
        return self.tables[self.collections_table].get_value_of_column_by_id(collection_id, "owner")

    def get_collection_by_name(self, name, parent=-1, owner=-1, public=-1, exact_match=False):
        filter_conditions =  [("name",name, exact_match)]
        if parent >= 0:
            filter_conditions.append(("parent",parent, True))
        if owner >= 0:
            filter_conditions.append(("owner",owner, True))
        if public >= 0:
            filter_conditions.append(("public",public, True))
        return self.tables[self.collections_table].get_record_list(["ID","name","type", "owner", "public"], filter_conditions)


    def get_collection_by_id(self, collection_id):
        return self.tables[self.collections_table].get_record_by_id(collection_id,["ID","name","type", "parent"])

    def replace_collection(self, input_data, collection_id):
        self.tables[self.collections_table].update_record(collection_id, input_data)
    