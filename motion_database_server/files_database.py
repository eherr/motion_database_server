if False:
    FILE_TABLES = dict()
    FILE_TABLES["data_files"] = [("name",TEXT_T),
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

    FILE_TABLES["data_types"] =  [("name",TEXT_T), # need to be unique
                    ("requirements",TEXT_T),
                    ("isModel",INT_T),
                    ("isTimeSeries",INT_T),
                    ("isSkeletonMotion",INT_T)
                    ]

    FILE_TABLES["data_loaders"] = [("dataType",TEXT_T),
                ("engine",TEXT_T),
                ("script",TEXT_T), 
                ("requirements",TEXT_T)]

    FILE_TABLES["data_transforms"] = [("name",TEXT_T),("script",TEXT_T),
                ("parameters",TEXT_T),
                ("requirements",TEXT_T),
                ("outputIsCollection",INT_T),
                ("outputType",TEXT_T)]

    FILE_TABLES["data_transform_inputs"] = [("dataTransform",INT_T),
                ("dataType",TEXT_T),
                ("isCollection",INT_T)]



class FilesDatabase:
    files_table = "files"   
    data_types_table = "data_types"
    data_loader_table = "data_loaders"
    data_transforms_table = "data_transforms"
    data_transform_inputs_table = "data_transform_inputs"
    def __init__(self, tables_desc):
        self.tables_desc = tables_desc
        for name in self.tables_desc:
            self.tables[name] = Table(self, name, self.tables_desc[name])

    def get_file_list_by_collection(self, collection, skeleton=None, dataType=None, is_model=None):
        filter_conditions =[("collection",str(collection))]
        join_statement = None
        cols = ["ID","name", "dataType"]
        if skeleton is not None:
            filter_conditions+=[("skeleton", skeleton)]
        if dataType is not None:
            filter_conditions+=[("dataType", dataType)]
        if is_model is not None:
            join_statement = " LEFT JOIN "+self.data_types_table+" ON  "+self.files_table+".dataType = "+self.data_types_table+".name"
            
            filter_conditions += [(self.data_types_table+".isModel", int(is_model)) ]
            cols = [self.files_table+".ID",self.files_table+".name", "dataType"]


        return self.tables[self.files_table].get_record_list(cols, filter_conditions=filter_conditions, join_statement=join_statement)
    
    def create_file(self, data):
        return self.tables[self.files_table].create_record(data)

    def get_file_by_id(self, f_id):
        r = self.tables[self.files_table].get_record_by_id(f_id, ["data"])
        data = None
        if r is not None:
            data = r[0]
        else:
            print("Error in get file data",m_id)
        return data

    def replace_file(self, f_id, data):
        self.tables[self.files_table].update_record(f_id, data)

    def delete_file_by_id(self, f_id):
        return self.tables[self.files_table].delete_record_by_id(f_id)
    
    def get_file_info(self, columns, file_ids):
        if "ID" not in columns:
            columns.append("ID")
        records = self.query_table(self.files_table, columns, [("ID",file_ids)])
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

    def get_data_type_list(self, is_model=None, is_skeleton_motion=None, is_time_series=None):
        filter_conditions = []
        if is_model is not None:
            filter_conditions+=[("isModel", is_model)]
        if is_skeleton_motion is not None:
            filter_conditions+=[("isSkeletonMotion", is_skeleton_motion)]
        if is_time_series is not None:
            filter_conditions+=[("isTimeSeries", is_time_series)]
        return self.tables[self.data_types_table].get_record_list(["name"], filter_conditions=filter_conditions)

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
        self.tables[self.data_loader_table].update_record_by_condition(conditions, input_data)
        
        conditions = [("outputType", dt)]
        input_data = dict()
        input_data["outputType"] = data["name"]
        self.tables[self.data_transforms_table].update_record_by_condition(conditions, input_data)
        
        conditions = [("dataType", dt)]
        input_data = dict()
        input_data["dataType"] = data["name"]
        self.tables[self.data_transform_inputs_table].update_record_by_condition(conditions, input_data)

        

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


    def get_data_transform_list(self):
        return self.tables[self.data_transforms_table].get_record_list(["ID","name","outputType", "outputIsCollection"])
    
    def create_data_transform(self, data):
        return self.tables[self.data_transforms_table].create_record(data)

    def edit_data_transform(self, dt_id, data):
        self.tables[self.data_transforms_table].update_record(dt_id, data)
    
    def get_data_transform_info(self, dt_id):
        cols = self.tables[self.data_transforms_table].cols
        record = self.tables[self.data_transforms_table].get_record_by_id(dt_id)
        if record is None:
            return None
        info = dict()
        for i, k in enumerate(cols):
            info[k] = record[i]
        return info
    
    def remove_data_transform(self, dt_id):
        return self.tables[self.data_transforms_table].delete_record_by_id(dt_id)

    def get_data_transform_input_list(self, dt_id):
        filter_conditions = []
        if dt_id is not None:
            filter_conditions+=[("dataTransform", dt_id)]
        return self.tables[self.data_transform_inputs_table].get_record_list(["ID", "dataType", "isCollection"], filter_conditions=filter_conditions)

    
    def create_data_transform_input(self, data):
        return self.tables[self.data_transform_inputs_table].create_record(data)

    def edit_data_transform_input(self, dti_id, data):
        self.tables[self.data_transform_inputs_table].update_record(dti_id, data)
    
    def get_data_transform_input_info(self, dti_id):
        cols = self.tables[self.data_transform_inputs_table].cols
        record = self.tables[self.data_transform_inputs_table].get_record(dti_id)
        if record is None:
            return None
        info = dict()
        for i, k in enumerate(cols):
            info[k] = record[i]
        return info
    
    def remove_data_transform_input(self, dti_id):
        return self.tables[self.data_transform_inputs_table].delete_record_by_id(dti_id)
    
