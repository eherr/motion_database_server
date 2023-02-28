from .schema import *

TABLES = dict()
TABLES["collections"] = COLLECT_TABLE
TABLES["skeletons"] = [("name",TEXT_T),
                    ("data",TEXT_T), 
                    ("metaData",TEXT_T),
                    ("owner",TEXT_T)
                    ]
TABLES["users"] = [("name",TEXT_T),
                    ("password",TEXT_T), 
                    ("role",TEXT_T), 
                    ("email",TEXT_T)]
TABLES["projects"] = [("name",TEXT_T), 
                    ("owner",INT_T),   
                    ("collection",INT_T),   
                    ("public",INT_T)]  
TABLES["project_members"] = [("user",INT_T), ("project",INT_T)] 




TABLES["files"] = [("name",TEXT_T),
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

TABLES["data_types"] =  [("name",TEXT_T), # need to be unique
                ("requirements",TEXT_T),
                ("isModel",INT_T),
                ("isTimeSeries",INT_T),
                ("isSkeletonMotion",INT_T),
                ("isProcessed",INT_T)
                ]

TABLES["data_loaders"] = [("dataType",TEXT_T),
            ("engine",TEXT_T),
            ("script",INT_T), 
            ("requirements",TEXT_T)]

TABLES["data_transforms"] = [("name",TEXT_T),
            ("script",TEXT_T),
            ("parameters",TEXT_T),
            ("requirements",TEXT_T),
            ("outputIsCollection",INT_T),
            ("outputType",TEXT_T)]

TABLES["data_transform_inputs"] = [("dataTransform",INT_T),
            ("dataType",TEXT_T),
            ("isCollection",INT_T)]


#experiments are instances of data transforms
TABLES["experiments"] = [("name",TEXT_T), # need to be unique
                    ("collection",INT_T), 
                    ("skeleton",INT_T), 
                    ("dataTransform",INT_T),
                    ("config",TEXT_T),   
                    ("logFile",TEXT_T),
                    ("logFields",TEXT_T),
                    ("externalURL",TEXT_T),  
                    ("owner", INT_T),
                    ("output",INT_T) # can be collection or file
                    ] 
TABLES["experiment_inputs"] = [
            ("dataTransformInput",INT_T),
            ("experiment",INT_T),
            ("input",INT_T)]

TABLES["tags"] =  [("name",TEXT_T), # need to be unique
                ]

TABLES["data_type_taggings"] =  [("tag",TEXT_T), # need to be unique
                                 ("dataType",TEXT_T)]
# download the inputs to folder
    #for each input if collection -> recursion
    #                else download file
# run script
# upload the outputs to db
# if file -> upload model as before 
# else if collection upload all file in output folder to collection
#single model already there

#assume output is restricted to single file or collection

#an experiment is an instance of a datatransform with a single output file
TABLES["model_graphs"] = [("name",TEXT_T),
                    ("project",INT_T), 
                    ("skeleton",INT_T), 
                    ("data",TEXT_T)]
TABLES["tags"] = [
            ("name",INT_T)]
TABLES["data_type_taggings"] = [
            ("dataType",TEXT_T),
            ("tag",INT_T)]