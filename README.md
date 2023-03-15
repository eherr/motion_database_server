# Motion Database Server

The Tornado-based web server provdes a REST interface to an SQLite database for the management of skeleton animation data and machine learning models using a collections, tags and skeletons. The database is integrated with [anim_utils](https://github.com/eherr/anim_utils) using a [Python client](https://github.com/eherr/motion_db_interface). To visualize the motions in the database a Unity WebGL client is provided.   


<p align="center">
  <img src="doc/images/webclient.gif">
</p>



To edit and annotate data in the database, the [motion_preprocessing_tool](https://github.com/eherr/motion_preprocessing_tool) can be used. Motion editing functions can also be registered as data transforms to be executed via the web client on a batch of motions.



## Setup Instructions

1. Install Python 3.6 or above in a virtual environment.

2. Clone the repository with all submodules. 
```bat
git clone --recursive git@github.com:eherr/motion_database_server.git
```

3. Install the base packages for [animation data editing](https://github.com/eherr/anim_utils) and [Python API](https://github.com/eherr/motion_db_interface.git)
```bat
pip install git+https://github.com/eherr/anim_utils

pip install git+https://github.com/eherr/motion_db_interface
```

4. Install other dependencies
```bat
pip install -r requirements.txt
```

5. Create a new empty database: 
```bat
python create_database.py PROJECT_NAME ADMIN_NAME ADMIN_PASSWORD ADMIN_EMAIL
```

6. Add a first skeleton using an example BVH file: 
```bat
python import_skeleton.py SKELETON_NAME BVH_FILE
```

7. Import BVH files from a directory specifying the previously imported skeleton:
```bat
python import_bvh_from_directory.py PROJECT_NAME SKELETON_NAME DIRECTORY_PATH
```

8. Start the web server: 
```bat
python main.py
```

10. Build the web client using angular: 
```bat
cd webclient 
ng build
```

10. Open the URL "localhost:8888" in browser to view the using the web client. Login using the admin user, to be able to upload motions. The port can be changed in db_server_config.json.

11. To upload and edit animations or upload and edit skeletons you can also use the [motion_preprocessing_tool](https://github.com/eherr/motion_preprocessing_tool).

## Publication
Herrmann, E., Du, H., Antalki, A., Rubinstein, D., Schubotz, R., Sprenger, J., Hosseini, S., Cheema, N., Zinnikus, I., Manns, M., Fischer, K. Slusallek, P., "Motion Data and Model Management for Applied Statistical Motion Synthesis" In: Proceedings of the Conference on Smart Tools and Applications in Computer Graphics. Eurographics Association, 2019.


## License
Copyright (c) 2019 DFKI GmbH.  
MIT License, see the LICENSE file.
