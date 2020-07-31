# FastAnnotation
A tool which aims to streamline the annotation process for computer vision projects dealing with Object Detection, Instance Segmentation and Semantic Segmentation.


## Installation 
### Requirements
Python 3.6 or greater

### Client
Note: For the following Installation steps please ensure pip is run with administrative privileges.

1. Kivy installation
    1. Windows:
        ```
        python -m pip install --upgrade pip wheel setuptools
        python -m pip install docutils pygments pypiwin32 kivy.deps.sdl2 kivy.deps.glew
        python -m pip install kivy.deps.gstreamer
        python -m pip install kivy.deps.angle
        python -m pip install kivy
        ```
    2. Ubuntu:
        ```
        python -m pip install -r client_requirements.txt
        ```

### Server
1. Flask installation
    
    1.Windows installation 
    ```
    python -m pip install flask
    python -m pip install flask-restplus
    python -m pip install flask_negotiate
    python -m pip install python-dateutil
    python -m pip install mysql-connector-python
    ```
   2. Ubuntu
   
   ```
   python -m pip install -r server_requirements.txt
   ```

2. MySql Installation
    1. Windows:
    ```
    TODO
    ```
    2. Ubuntu:
        1. Install mysql
            ```
            sudo apt-get install mysql-workbench
            ```
        1. Create a connection to the database and run the `database/create_database.sql` script
        1. (Optional) run the 'database/create_test_data.sql' script to populate tables with test data
    3. Alternatively, Docker can be used to run a MySQL database for development. 
        1. Download and install Docker and Docker Compose
        2. Start the container with
        ```
       >> docker-compose up
       ```
       3. Stop the container with
       ```
       >> docker-compose down
       ```
       4. To stop the container and delete the volume (deleting all data in the DB)
       ```
       >> docker-compose down -v
       ```
## Build

### Linux builds
Prior to any linux builds please install the appropriate python dev tools and upgrade setuptools. (Replace python verson as required)
```
pip install --upgrade setuptools
apt-get install python3.6-dev
```
### Client
1. Install Pyinstaller (if required)
```
pip install pyinstaller
```
2. Navigate to [build_scripts](build_scripts)
```
pyinstaller --clean client.spec
```
3. Move zip to desired location
### Server
1. Install Pyinstaller (if required)
```
pip installer pyinstaller
```
2. Navigate to [build_scripts](build_scripts)
```
pyinstaller --clean server.spec
```
3. Move zip to desired location
