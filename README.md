# Motion Management Database Server

The Tornado-based web server provdes a REST interface to an SQLite database for the management of skeleton animation data and statistical motion models. To visualize the motions in the database, a Unity WebGL client is provided.  
To edit and annotate data in the database, the [motion_preprocessing_tool](https://github.com/eherr/motion_preprocessing_tool) can be used. We plan to move the motion editing functionality into the web client.


More details can be found in this paper:  
Herrmann, E., Du, H., Antalki, A., Rubinstein, D., Schubotz, R., Sprenger, J., Hosseini, S., Cheema, N., Zinnikus, I., Manns, M., Fischer, K. Slusallek, P., "Motion Data and Model Management for Applied Statistical Motion
Synthesis" In: Proceedings of the Conference on Smart Tools and Applications in Computer Graphics. Eurographics Association, 2019.
  
  
## Setup Instructions

1. Install Python 3.5 in a virtual environment.

2. Clone the repository with all submodules. The mgrd submodule of morphablegraphs is optional and can be ignored.
```bat
git clone --recursive git@github.com:eherr/motion_database_server.git
```

3. Install the dependencies
```bat
pip install -r requirements.txt
```

4. Create a new empty database: 
```bat
python create_database.py
```

5. Add a first user for remote database editing: 
```bat
python create_user.py root password admin none
```

6. Add a first skeleton using an example BVH file: 
```bat
python import_skeleton.py skeleton_name bvh_filename
```

7. Import BVH files from a directory specifying the previously imported skeleton:
```bat
python import_bvh_from_directory.py skeleton_name directory_path
```

8. Start the web server: 
```bat
python run_motion_db_server_standalone.py
```

9. Build the web client using angular: 
```bat
cd webclient 
ng build
```

10. Open the URL "localhost:8888" in browser to view the using the web client. Login using the admin user, to be able to upload motions. The port can be changed in db_server_config.json.

11. To upload and edit animations or upload and edit skeletons you can also use the [motion_preprocessing_tool](https://github.com/eherr/motion_preprocessing_tool).
## License
Copyright (c) 2019 DFKI GmbH.  
MIT License, see the LICENSE file.
