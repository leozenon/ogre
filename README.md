O.G.R.E.
========

OGRE is an ebook storage and synchronisation service. It helps a group maintain a single set of ebooks across many users.

OGRE comes in two parts:
  - a server built in python relying on Flask and Celery
  - a cross-platform client script (again in python) which synchronises ebooks to the server.


Ogreserver Prerequisites
------------------------

* aptitude install virtualenvwrapper python-pip python-dev
* aptitude install rabbitmq-server
* aptitude install mysql-server libmysqlclient-dev


Ogreserver Install
------------------

0. Create a directory for this project:

    ```bash
    mkdir -p /srv/www
    cd /srv/www
    ```

1. Clone this repo:

    ```bash
    git clone git@github.com:mafrosis/ogre.git
    git checkout develop
    ```

2. Init a virtualenv for OGRE:

    ```bash
    $ mkvirtualenv ogre
    $ pip install -r config/requirements.txt
    ```

3. Create the auth DB:

    ```bash
    $ mysql -u root -p < config/schema-mysql2.sql
    ```

4. Start gunicorn as a development server:

    ```bash
    $ gunicorn ogreserver:app -b 127.0.0.1:8005
    ```

5. Start celeryd to process background tasks:

    ```bash
    $ celery worker --app=ogreserver
    ```

6. Create yourself a new user for OGRE:

    ```bash
    $ ./manage.py create_user <username> <password> <email_address>
    ```

7. You should then be able to view and log into the website at:

    ```bash
    http://127.0.0.1:8005/ogre
    ```

Troubleshooting
---------------



