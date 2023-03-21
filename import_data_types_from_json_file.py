
import argparse
from motion_database_server.schema import DBSchema, TABLES
from motion_database_server.utils import load_json_file
from motion_database_server.motion_file_database import MotionFileDatabase
from motion_database_server.data_transform_database import DataTransformDatabase


def import_data_types(db_path, data):
    schema = DBSchema(TABLES)
    motion_db = MotionFileDatabase(schema)
    motion_db.connect_to_database(db_path)
    motion_db.data_types_from_dict(data)
    motion_db.close()

    data_transform_db = DataTransformDatabase(schema)
    data_transform_db.connect_to_database(db_path)
    data_transform_db.data_transforms_from_dict(data["data_transforms"])
    data_transform_db.close()
    return data


CONFIG_FILE = "db_server_config.json"
if __name__ == "__main__":
    config = load_json_file(CONFIG_FILE)
    db_path = config["db_path"]
    parser = argparse.ArgumentParser(description='Import data types to db.')
    parser.add_argument('filename', help='Filename')
    args = parser.parse_args()
    if args.filename is not None:
        data_types = load_json_file(args.filename)
        import_data_types(db_path, data_types)
    