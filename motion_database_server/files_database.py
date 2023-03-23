import os
from pathlib import Path
from .table import Table

class FilesDatabase:
    files_table = "files"   
    data_types_table = "data_types"
    data_loader_table = "data_loaders"
    tags_table = "tags"
    data_type_taggings_table = "data_type_taggings"
    def __init__(self, tables_desc):
        self.tables_desc = tables_desc
        for name in self.tables_desc:
            self.tables[name] = Table(self, name, self.tables_desc[name])

    def get_file_list(self, collection=None, skeleton=None, dataType=None, tags=None):
        filter_conditions = []
        intersection_list = []
        join_statement = None
        cols = ["ID","name", "dataType"]
        if collection is not None:
            filter_conditions+=[("collection", str(collection))]
        if skeleton is not None:
            filter_conditions+=[("skeleton", skeleton)]
        if dataType is not None:
            filter_conditions+=[("dataType", dataType)]
        if tags is not None:# join data types and tagging tables to filter data types based on tags
            join_statement = " LEFT JOIN "+self.data_types_table+" ON  "+self.files_table+".dataType = "+self.data_types_table+".name"
            join_statement += " LEFT JOIN "+self.data_type_taggings_table+" ON "+self.data_types_table+".name = "+ self.data_type_taggings_table + ".dataType"
            #filter_conditions += [(self.data_types_table+".isModel", int(is_model)) ]
            cols = [self.files_table+".ID",self.files_table+".name", self.files_table+".dataType"]
            
            for tag in tags:
                intersection_list += [(self.data_type_taggings_table+".tag", tag) ]
        return self.tables[self.files_table].get_record_list(cols, filter_conditions=filter_conditions,intersection_list=intersection_list, join_statement=join_statement, distinct=True)
    
    def create_file(self, data):
        return self.tables[self.files_table].create_record(data)

    def get_file_by_id(self, f_id):
        r = self.tables[self.files_table].get_record_by_id(f_id, ["data"])
        data = None
        if r is not None:
            data = r[0]
        else:
            print("Error in get file data",f_id)
        return data

    def replace_file(self, f_id, data):
        self.tables[self.files_table].update_record(f_id, data)

    def delete_file_by_id(self, f_id):
        return self.tables[self.files_table].delete_record_by_id(f_id)
    
    def get_file_info(self, columns, file_id):
        if "ID" not in columns:
            columns.append("ID")
        records = self.query_table(self.files_table, columns, [("ID",file_id)])
        result = dict()
        for r in records:
            row = dict()
            r_id = -1
            for idx, col in enumerate(columns):
                if col == "ID":
                    r_id = int(r[idx])
                else:
                    row[col] = int(r[idx])
            result[r_id] = row
        return result

    def get_owner_of_file(self, f_id):
        collection_id = self.tables[self.files_table].get_value_of_column_by_id(f_id, "collection")
        if collection_id is None:
            return None
        return self.get_owner_of_collection(collection_id)

    def get_data_type_list(self, tags=None):
        filter_conditions = []
        join_statement = None
        if tags is not None:
            join_statement = " LEFT JOIN "+self.data_type_taggings_table+" ON  "+self.data_types_table+".dataType = "+self.data_type_taggings_table+".dataType"
            for tag in tags:
                filter_conditions += [(self.data_type_taggings_table+".tag", tag) ]
        return self.tables[self.data_types_table].get_record_list(["name"], filter_conditions=filter_conditions, join_statement=join_statement, distinct=True)

    def create_data_type(self, data):
        name = data["name"]
        records = self.tables[self.data_types_table].search_records_by_name(name, exact_match=True)
        if len(records) > 0:
            return -1
        record_data = dict()
        for col in data:
            if col in self.tables[self.data_types_table].cols:
                record_data[col] = data[col]
        return self.tables[self.data_types_table].create_record(record_data)

    def remove_data_type(self, dt):
        print("remove dataType", dt)
        self.tables[self.data_types_table].delete_record_by_name(dt)
        condition_list = [("dataType", dt)]
        self.tables[self.data_loader_table].delete_record_by_condition(condition_list)
    
    def edit_data_type(self, dt, data):
        self.tables[self.data_types_table].update_record_by_name(dt, data)#
        conditions = [("dataType", dt)]
        if "name" not in data:
            return
        # rename in other tables
        input_data = dict()
        input_data["dataType"] = data["name"]
        self.tables[self.files_table].update_record_by_condition(conditions, input_data)

        input_data = dict()
        input_data["dataType"] = data["name"]
        self.tables[self.data_loader_table].update_record_by_condition(conditions, input_data)

        input_data = dict()
        input_data["dataType"] = data["name"]
        self.tables[self.data_type_taggings_table].update_record_by_condition(conditions, input_data)
        

    def get_data_type_info(self, dt):
        return self.tables[self.data_types_table].get_full_record_by_name(dt)

    def get_data_loader_list(self):
        return self.tables[self.data_loader_table].get_record_list(["ID", "dataType","engine"])
    
    def create_data_loader(self, data):
        return self.tables[self.data_loader_table].create_record(data)

    def edit_data_loader(self, dt,engine, data):
        condition_list = [("dataType", dt), ("engine", engine)]
        self.tables[self.data_loader_table].update_record_by_condition(condition_list, data)
    
    def get_data_loader_info(self, dt, engine):
        condition_list = [("dataType", dt), ("engine", engine)]
        cols = self.tables[self.data_loader_table].cols
        record = self.tables[self.data_loader_table].get_record_by_condition(condition_list, cols)
        if record is None:
            return None
        info = dict()
        for i, k in enumerate(cols):
            info[k] = record[i]
        return info
    
    def remove_data_loader(self, mt, engine):
        condition_list = [("dataType", mt), ("engine", engine)]
        return self.tables[self.data_loader_table].delete_record_by_condition(condition_list)

    def get_tag_list(self):
        return self.tables[self.tags_table].get_record_list(["name"])
    
    def create_tag(self, tag):
        data = dict()
        data["name"] = tag
        return self.tables[self.tags_table].create_record(data)
    
    def rename_tag(self, old_tag, new_tag):
        data = dict()
        data["name"] = new_tag
        self.tables[self.tags_table].update_record_by_name(old_tag, data)
        data = dict()
        data["tag"] = new_tag
        conditions = [("tag", old_tag)]
        self.tables[self.data_type_taggings_table].update_record_by_condition(conditions, data)
        
    
    def remove_tag(self, tag):
        self.tables[self.tags_table].delete_record_by_name(tag)
        condition = [("tag",tag)]
        return self.tables[self.data_type_taggings_table].delete_record_by_condition(condition)
    
    def get_data_type_tag_list(self, data_type):
        filter_conditions=[("dataType", data_type)]
        return self.tables[self.data_type_taggings_table].get_record_list(["tag"], filter_conditions=filter_conditions)

    
    def add_data_type_tag(self, data_type, tag):
        data = dict()
        data["tag"] = tag
        data["dataType"] = data_type
        return self.tables[self.data_type_taggings_table].create_record(data)

    def remove_data_type_tag(self, data_type, tag=None):
        condition = [("dataType",data_type)]
        if tag is not None:
            condition += [("tag",tag)]
        return self.tables[self.data_type_taggings_table].delete_record_by_condition(condition)

    def has_tag(self, data_type, tag):
        condition = [("dataType",data_type), ("tag", tag)]
        tag_records = self.tables[self.data_type_taggings_table].get_record_by_condition(condition, ["ID"])
        return tag_records is not None and len(tag_records)> 0
    
    def check_file_consistency(self):
        p = Path(self.data_dir + os.sep + self.files_table)
        data_files = list(map(str, [f.name for f in p.glob("**/*.data")]))
        meta_data_files = list(map(str, [f.name for f in p.glob("**/*.metaData")]))
        data_files_ref, meta_data_files_ref = self.get_file_references()
        data_delta = set(data_files).difference(data_files_ref)
        meta_data_delta = set(meta_data_files).difference(meta_data_files_ref)
        missing_files = [ f for f in data_delta if f not in data_files]
        missing_meta_files = [ f for f in meta_data_delta if f not in meta_data_files]

        missing_references = [ f for f in data_delta if f not in data_files_ref]
        missing_meta_references = [ f for f in meta_data_delta if f not in meta_data_files_ref]

        print("missing_files",missing_files)
        print("missing_meta_files",missing_meta_files)
        print("missing_references",missing_references)
        print("missing_meta_references",missing_meta_references)

    def get_file_references(self):
        records = self.tables[self.files_table].db.query_table(self.files_table, ["data", "metaData"], [])
        return zip(*records)
    
    def has_data_file(self, file_name):        
        condition = [("data",file_name)]
        file_record = self.tables[self.files_table].get_record_by_condition(condition, ["ID"])
        return file_record is not None
    
    def has_meta_data_file(self, file_name):        
        condition = [("metaData",file_name)]
        file_record = self.tables[self.files_table].get_record_by_condition(condition, ["ID"])
        return file_record is not None

    def data_types_to_dict(self):
        data = dict()
        data["tags"] = [t for t, in self.get_tag_list()]
        data["data_types"] = dict()
        for name, in self.get_data_type_list():
            t_info = self.get_data_type_info(name)
            t_info["tags"] = [t for t, in self.get_data_type_tag_list(name)]
            data["data_types"][name] = t_info

        data["data_loaders"] = dict()
        for idx, t,engine in self.get_data_loader_list():
            data["data_loaders"][(t + ":" + engine)] = self.get_data_loader_info(t, engine)
        return data
    
    def data_types_from_dict(self, data):
        for tag in data["tags"]:
            self.create_tag(tag)
        for name in data["data_types"]:
            self.create_data_type(data["data_types"][name])
            for tag in data["data_types"][name]["tags"]:
                self.add_data_type_tag(name, tag)
        for name in data["data_loaders"]:
            self.create_data_loader(data["data_loaders"][name])
