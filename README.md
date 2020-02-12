# FastAnnotation
A tool which aims to streamline the annotation process for computer vision projects dealing with Object Detection, Instance Segmentation and Semantic Segmentation.


## Installation 

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
        python -m pip install --upgrade pip wheel setuptools
        python -m pip install kivy
        ```

### Server
1. Flask installation
    ```
    python -m pip install flask
    python -m pip install flask_negotiate
<<<<<<< HEAD
=======
    python -m pip install mysql-connector-python
>>>>>>> develop
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
    
             
