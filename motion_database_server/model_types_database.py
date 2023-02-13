import os

class ModleTypesDatabase:
    model_types_table = "model_types"
    eval_scripts_table = "model_evaluation_scripts"

    def get_model_type_list(self):
        return self.tables[self.model_types_table].get_record_list(["name"], distinct=True)

    def create_model_type(self, data):
        name = data["name"]
        records = self.tables[self.model_types_table].search_records_by_name(name, exact_match=True)
        if len(records) > 0:
            return -1
        record_data = dict()
        for col in data:
            if col in self.tables[self.model_types_table].cols:
                record_data[col] = data[col]
        return self.tables[self.model_types_table].create_record(record_data)

    def remove_model_type(self, mt):
        print("remove_model_type", mt)
        self.tables[self.model_types_table].delete_record_by_name(mt)
        condition_list = [("modelType", mt)]
        self.tables[self.eval_scripts_table].delete_record_by_condition(condition_list)

    def edit_model_type(self, mt, data):
        self.tables[self.model_types_table].update_record_by_name(mt, data)
    
    def get_model_type_info(self, mt):
        info = self.tables[self.model_types_table].get_full_record_by_name(mt)
        #condition_list = [("modelType", mt)]
        #eval_scripts = self.tables[self.eval_scripts_table].get_record_list(["script", "requirements"],condition_list=intersection_list)
        #info["eval_scripts"] = eval_scripts
        return info

    def get_eval_script_list(self):
        return self.tables[self.eval_scripts_table].get_record_list(["modelType","engine"], distinct=False)

    def create_eval_script(self, data):
        record_data = dict()
        for col in data:
            if col in self.tables[self.eval_scripts_table].cols:
                record_data[col] = data[col]
        return self.tables[self.eval_scripts_table].create_record(record_data)

    def edit_eval_script(self, mt, engine, data):
        condition_list = [("modelType", mt), ("engine", engine)]
        return self.tables[self.eval_scripts_table].update_record_by_condition(condition_list, data)


    def get_eval_script_info(self, mt, engine):
        condition_list = [("modelType", mt), ("engine", engine)]
        cols = self.tables[self.eval_scripts_table].cols
        record = self.tables[self.eval_scripts_table].get_record_by_condition(condition_list)
        if record is None:
            return None
        info = dict()
        for i, k in enumerate(cols):
            info[k] = record[i]
        return info

    def remove_eval_script(self, mt, engine):
        condition_list = [("modelType", mt), ("engine", engine)]
        return self.tables[self.eval_scripts_table].delete_record_by_condition(condition_list)
