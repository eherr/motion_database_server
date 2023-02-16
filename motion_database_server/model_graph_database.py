

import bson
import bz2
import numpy as np

class ModelGraphDatabase(): 
    graph_table = "model_graphs"
    def get_graph_list(self, skeleton=""):
        filter_conditions = []
        if skeleton != "":
            filter_conditions+=[("skeleton", skeleton)]
        return self.tables[self.graph_table].get_record_list(["ID","name"], filter_conditions)
    
    def add_new_graph(self, name, skeleton, graph_data):
        record_data = dict()
        record_data["name"] = name
        record_data["skeleton"] = skeleton
        record_data["data"] = graph_data
        return self.tables[self.graph_table].create_record(record_data)

    def replace_graph(self, graph_id, input_data):
        if "data" in input_data:
            graph_data = bz2.compress(bson.dumps(input_data["data"]))
            input_data["data"] = graph_data
        self.tables[self.graph_table].update_record(graph_id, input_data)

    def get_graph_by_id(self, graph_id):
        records = self.tables[self.graph_table].get_record_by_id(graph_id, ["data"])
        data = None
        if len(records) > 0:
            data = records[0]
            data = bz2.decompress(data)
            data = bson.loads(data)
        return data

    def remove_graph_by_id(self, graph_id):
        return self.tables[self.graph_table].delete_record_by_id(graph_id)

