
import argparse
from motion_database_server.schema import DBSchema, TABLES
from motion_database_server.utils import load_json_file, save_json_file
from motion_database_server.motion_file_database import MotionFileDatabase
from motion_database_server.data_transform_database import DataTransformDatabase

def export_data_types(db_path):
    schema = DBSchema(TABLES)
    motion_db = MotionFileDatabase(schema)
    motion_db.connect_to_database(db_path)
    data = dict()
    data["tag_list"] = motion_db.get_tag_list()
    data["data_types"] = dict()
    for name, in motion_db.get_data_type_list():
        t_info = motion_db.get_data_type_info(name)
        t_info["tags"] = motion_db.get_data_type_tag_list(name)
        data["data_types"][name] = t_info

    data["data_loaders"] = dict()
    for idx, t,engine in motion_db.get_data_loader_list():
         data["data_loaders"][(t + ":" + engine)] = motion_db.get_data_loader_info(t, engine)
    motion_db.close()
    data_transform_db = DataTransformDatabase(schema)
    data_transform_db.connect_to_database(db_path)
    data["data_transforms"] = dict()
    for idx, dt_name, output_t, output_is_collection in data_transform_db.get_data_transform_list():
        data["data_transforms"][dt_name] = data_transform_db.get_data_transform_info(idx)
        dt_inputs = []
        for idx, input_t, is_collection in data_transform_db.get_data_transform_input_list(idx):
            dt_inputs.append([input_t, is_collection])
        data["data_transforms"][dt_name]["inputs"] = dt_inputs
    data_transform_db.close()
    return data



CONFIG_FILE = "db_server_config.json"
if __name__ == "__main__":
    config = load_json_file(CONFIG_FILE)
    db_path = config["db_path"]
    parser = argparse.ArgumentParser(description='Export data types from db.')
    parser.add_argument('filename', help='Filename')
    args = parser.parse_args()
    if args.filename is not None:
        data_types = export_data_types(db_path)
        print(data_types)
        save_json_file(data_types, args.filename)
    