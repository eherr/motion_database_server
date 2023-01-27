import os
import json
import numpy as np
from datetime import datetime
from csv import DictWriter


class ExperimentDatabase:
    
    experiments_table = "experiments"
    def create_experiment(self, data):
        # project_id, collection_id, skeleton, name, owner, code_url, start_cmd, config, resources
        if "name" not in data:
            print("Error missing name field")
            return -1
        name = data["name"]
        records = self.tables[self.experiments_table].search_records_by_name(name, ["name"], True)
        if len(records) > 0:
            data["name"] = name +"_" + str(len(records))
        record_data = dict()
        for col in data:
            if col in self.tables[self.experiments_table].cols:
                record_data[col] = data[col]

        if "externalURL" not in record_data:
            record_data["externalURL"] = ""
        if "model" not in record_data:
            record_data["model"] = -1
        if "config" in record_data:
            record_data["config"] = json.dumps(record_data["config"])
        if "clusterConfig" in record_data:
            record_data["clusterConfig"] = json.dumps(record_data["clusterConfig"])
        record_data["logFile"] = ""
        return self.tables[self.experiments_table].create_record(record_data)

    def remove_experiment(self, exp_id):
        print("remve experiment", exp_id)
        record = self.tables[self.experiments_table].get_record_by_id(exp_id, ["logFile", "model"])
        if record is None:
            return
        logfile = record[0]
        model_id = record[1]
        filename = self.data_dir + os.sep + self.experiments_table + os.sep + logfile
        print("remve experiment", filename)
        if os.path.isfile(filename):
            os.remove(filename)
        self.tables[self.experiments_table].delete_record_by_id(exp_id)
        if model_id > -1:
            self.tables[self.model_table].delete_record_by_id(model_id)

    def edit_experiment(self, exp_id, data):
        record_data = dict()
        for col in data:
            if col in self.tables[self.experiments_table].cols:
                record_data[col] = data[col]
        self.tables[self.experiments_table].update_record(exp_id, data)
    
    def append_experiment_log(self, exp_id, log_entry):
        # get or create log file name
        record = self.tables[self.experiments_table].get_record_by_id(exp_id, ["name", "logFile", "logFields"])
        if record is None:
            return
        exp_name, logfile, field_names = record
        write_header = False
        if logfile  is None or logfile == "":
            timestr = datetime.now().strftime("%m-%d-%Y_%H-%M-%S")
            logfile = exp_name + "_" +str(exp_id)+ "_"+timestr + ".csv"
            field_names = json.dumps(list(log_entry.keys()))
            data = {"logFile":logfile,"logFields":field_names}
            self.tables[self.experiments_table].update_record(exp_id, data)
            write_header = True
        ## append row
        field_names = json.loads(field_names)
        
        print("append log file", logfile)
        with open(self.data_dir + os.sep + self.experiments_table + os.sep + logfile, 'a') as f:
            csv_writer = DictWriter(f, fieldnames=field_names)
            if write_header: 
                csv_writer.writeheader()
            csv_writer.writerow(log_entry)
            f.close()

    def get_experiment_log(self, exp_id):
        record = self.tables[self.experiments_table].get_record_by_id(exp_id, ["logFile", "logFields"])
        if record is None:
            return
        logfile, field_names = record[0], record[1]
        filename = self.data_dir + os.sep + self.experiments_table + os.sep + logfile
        if os.path.isfile(filename):
            data = np.loadtxt(filename, skiprows=1, delimiter=',')
            data = data.tolist()
            field_names = json.loads(field_names)
            return field_names, data
        else:
            return None

    def get_experiment_list(self, collection_id=None, skeleton=None):
        intersection_list = []
        if collection_id is not None:
            intersection_list += [("collection", collection_id)]
        if skeleton is not None:
            intersection_list += [ ("skeleton", skeleton)]
        return self.tables[self.experiments_table].get_record_list(["ID", "name"], intersection_list=intersection_list,distinct=True)
    
    def get_experiment_info(self, exp_id):
        cols = self.tables[self.experiments_table].cols
        record = self.tables[self.experiments_table].get_record_by_id(exp_id, cols)
        if record is None:
            return None
        data = dict()
        for i, k in enumerate(cols):
            data[k] = record[i]
        return data

    def get_experiment_owner(self, exp_id):
        owner = self.tables[self.experiments_table].get_value_of_column_by_id(exp_id, "owner")
        if owner is None:
            return -1
        else:
            return owner
# create experiment
# run
# edit data to set_model, log data and external url
# set external url