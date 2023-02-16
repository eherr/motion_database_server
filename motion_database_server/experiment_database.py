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
import os
import json
import numpy as np
from datetime import datetime
from csv import DictWriter
if False:
    EXP_TABLES["experiments"] = [("name",TEXT_T), # need to be unique
                        ("collection",INT_T), 
                        ("skeleton",INT_T), 
                        ("dataTransform",INT_T)
                        ("config",TEXT_T),   
                        ("owner",INT_T),   
                        ("logFile",TEXT_T),
                        ("logFields",TEXT_T),
                        ("externalURL",TEXT_T),  
                        ("output",INT_T) # can be collection or file
                        ] 
    EXP_TABLES["experiment_inputs"] = [
                ("dataTransformInput",INT_T),
                ("experiment",INT_T),
                ("input",INT_T)]

class ExperimentDatabase:
    
    experiments_table = "experiments"
    experiment_inputs_table = "experiments_inputs"
    def create_experiment(self, data):
        if "name" not in data:
            print("Error missing name field")
            return -1
        name = data["name"]
        records = self.tables[self.experiments_table].search_records_by_name(name, exact_match=True)
        if len(records) > 0:
            data["name"] = name +"_" + str(len(records))
        record_data = dict()
        for col in data:
            if col in self.tables[self.experiments_table].cols:
                record_data[col] = data[col]

        if "externalURL" not in record_data:
            record_data["externalURL"] = ""
        if "output" not in record_data:
            record_data["output"] = -1
        if "config" in record_data:
            record_data["config"] = json.dumps(record_data["config"])
        record_data["logFile"] = ""
        return self.tables[self.experiments_table].create_record(record_data)

    def remove_experiment(self, exp_id):
        print("remve experiment", exp_id)
        record = self.tables[self.experiments_table].get_record_by_id(exp_id, ["logFile", "output"])
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
            self.tables[self.files_table].delete_record_by_id(model_id)

    def edit_experiment(self, exp_id, data):
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

    def get_experiment_list(self, project=None, collection=None, skeleton=None):
        intersection_list = []
        if project is not None:
            intersection_list += [("project", project)]
        if collection is not None:
            intersection_list += [("collection", collection)]
        if skeleton is not None:
            intersection_list += [ ("skeleton", skeleton)]
        return self.tables[self.experiments_table].get_record_list(["ID", "name"], intersection_list=intersection_list,distinct=True)
    
    def get_experiment_info(self, exp_id):
        return self.tables[self.experiments_table].get_full_record_by_id(exp_id)

    def get_experiment_owner(self, exp_id):
        owner = self.tables[self.experiments_table].get_value_of_column_by_id(exp_id, "owner")
        if owner is None:
            return -1
        else:
            return owner

    def get_experiment_input_list(self, exp_id):
        filter_conditions = []
        if exp_id is not None:
            filter_conditions+=[("experiment", exp_id)]
        return self.tables[self.experiment_inputs_table].get_record_list(["ID", "dataTransformInput","experiment", "input"], filter_conditions=filter_conditions)

    def create_experiment_input(self, data):
        return self.tables[self.experiment_inputs_table].create_record(data)

    def edit_experiment_input(self, expi_id, data):
        self.tables[self.experiment_inputs_table].update_record(expi_id, data)
    
    def get_experiment_input_info(self, dti_id):
        cols = self.tables[self.experiment_inputs_table].cols
        record = self.tables[self.experiment_inputs_table].get_record(dt_id)
        if record is None:
            return None
        info = dict()
        for i, k in enumerate(cols):
            info[k] = record[i]
        return info
    
    def remove_experiment_input(self, expi_id):
        return self.tables[self.experiment_inputs_table].delete_record(expi_id)
    

# create experiment
# run
# edit data to set_model, log data and external url
# set external url