
import argparse
from motion_database_server.schema import DBSchema, TABLES
from motion_database_server.utils import load_json_file
from motion_database_server.motion_file_database import MotionFileDatabase
from motion_database_server.data_transform_database import DataTransformDatabase


def import_data_types(db_path, data):
    schema = DBSchema(TABLES)
    motion_db = MotionFileDatabase(schema)
    motion_db.connect_to_database(db_path)
    for tag in data["tags"]:
        motion_db.create_tag(tag)
    for name in data["data_types"]:
        motion_db.create_data_type(data["data_types"][name])
        for tag in data["data_types"][name]["tags"]:
            #print(name, tag)
            motion_db.add_data_type_tag(name, tag)
    for name in data["data_loaders"]:
        motion_db.create_data_loader(data["data_loaders"][name])
    motion_db.close()

    data_transform_db = DataTransformDatabase(schema)
    data_transform_db.connect_to_database(db_path)
    for name in data["data_transforms"]:
        dt_idx = data_transform_db.create_data_transform(data["data_transforms"][name])
        for input_t, is_collection in data["data_transforms"][name]["inputs"]:
            dt_input = {"dataTransform": dt_idx, "dataType": input_t, "isCollection": is_collection}
            data_transform_db.create_data_transform_input(dt_input)
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
    