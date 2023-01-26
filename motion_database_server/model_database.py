



class ModelDatabase:
    model_table = "models"    
    
    def get_model_list_by_collection(self, collection, skeleton="", format="mm"):
        filter_conditions =[("collection",str(collection)), ("format", format)]
        if skeleton != "":
            filter_conditions+=[("skeleton", skeleton)]
        r = self.query_table(self.model_table, ["ID","name"], filter_conditions)
        return r

    def delete_model_by_id(self, m_id):
        return self.tables[self.model_table].delete_record_by_id(m_id)

    def get_model_by_id(self, m_id):
        r = self.tables[self.model_table].get_record_by_id(m_id, ["data"])
        data = None
        if r is not None:
            data = r[0]
        else:
            print("Error in get model data",m_id)
        return data

    def replace_model(self, m_id, data):
        self.tables[self.model_table].update_record(m_id, data)

    def upload_model(self,data):
        record_data = dict()
        if "format" not in data:
            data["format"] = "mm"
        return self.tables[self.model_table].create_record(record_data)

    def get_owner_of_model(self, model_id):
        collection_id = self.tables[self.model_table].get_value_of_column_by_id(model_id, "collection")
        if collection_id is None:
            return None
        return self.get_owner_of_collection(collection_id)
