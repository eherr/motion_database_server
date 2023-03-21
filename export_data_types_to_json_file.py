
import argparse
from motion_database_server.schema import DBSchema, TABLES
from motion_database_server.utils import load_json_file, save_json_file
from motion_database_server.motion_file_database import MotionFileDatabase
from motion_database_server.data_transform_database import DataTransformDatabase

def export_data_types(db_path):
    schema = DBSchema(TABLES)
    motion_db = MotionFileDatabase(schema)
    motion_db.connect_to_database(db_path)
    data = motion_db.data_types_to_dict()
    motion_db.close()
    data_transform_db = DataTransformDatabase(schema)
    data_transform_db.connect_to_database(db_path)
    data["data_transforms"] = data_transform_db.data_transforms_to_dict()
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
    