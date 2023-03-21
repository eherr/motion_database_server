
from motion_database_server.schema import DBSchema, TABLES
from motion_database_server.table import Table
from motion_database_server.database_wrapper import DatabaseWrapper

class DataTransformDatabase(DatabaseWrapper):
    data_transforms_table = "data_transforms"
    data_transform_inputs_table = "data_transform_inputs"
    
    def __init__(self, schema=None):
        DatabaseWrapper.__init__(self)
        if schema is None:
            schema = DBSchema(TABLES)
        self.schema =schema
        self.tables = dict()
        for name in self.schema.tables:
            self.tables[name] = Table(self, name, self.schema.tables[name])
    
    def get_data_transform_list(self):
        return self.tables[self.data_transforms_table].get_record_list(["ID","name","outputType", "outputIsCollection"])
    
    def create_data_transform(self, data):
        return self.tables[self.data_transforms_table].create_record(data)

    def edit_data_transform(self, dt_id, data):
        self.tables[self.data_transforms_table].update_record(dt_id, data)
    
    def get_data_transform_info(self, dt_id):
        cols = self.tables[self.data_transforms_table].cols
        record = self.tables[self.data_transforms_table].get_record_by_id(dt_id, cols)
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
    
    def rename_data_type(self, old_name, new_name):
        conditions = [("outputType", old_name)]
        input_data = dict()
        input_data["outputType"] = new_name
        self.tables[self.data_transforms_table].update_record_by_condition(conditions, input_data)
        
        conditions = [("dataType", old_name)]
        input_data = dict()
        input_data["dataType"] = new_name
        self.tables[self.data_transform_inputs_table].update_record_by_condition(conditions, input_data)

    def data_transforms_to_dict(self):
        data = dict()
        for idx, dt_name, output_t, output_is_collection in self.get_data_transform_list():
            data[dt_name] = self.get_data_transform_info(idx)
            dt_inputs = []
            for idx, input_t, is_collection in self.get_data_transform_input_list(idx):
                dt_inputs.append([input_t, is_collection])
            data[dt_name]["inputs"] = dt_inputs
        return data
    
    def data_transforms_from_dict(self, data):
        for name in data:
            dt_idx = self.create_data_transform(data[name])
            for input_t, is_collection in data[name]["inputs"]:
                dt_input = {"dataTransform": dt_idx, "dataType": input_t, "isCollection": is_collection}
                self.create_data_transform_input(dt_input)