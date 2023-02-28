

class DataTransformDatabase:
    data_transforms_table = "data_transforms"
    data_transform_inputs_table = "data_transform_inputs"
    
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
    