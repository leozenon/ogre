O.G.R.E.
========

OGRE is an ebook storage and synchronisation service. It helps a group maintain a single set of ebooks across many users.

OGRE comes in two parts:
  - a server built in python relying on Flask and Celery
  - a cross-platform client script (again in python) which synchronises ebooks to the server.


Ogreserver Prerequisites
------------------------

* aptitude install virtualenvwrapper python-pip python-dev
* aptitude install libevent-dev
* aptitude install rabbitmq-server
* aptitude install mysql-server libmysqlclient-dev
* aptitude install supervisor


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
    cd ogre/ogreserver
    git checkout develop
    ```

2. Init a virtualenv for OGRE:

    ```bash
    $ mkvirtualenv ogre
    $ pip install -r config/requirements.txt
    ```

3. Create the auth DB:

    ```bash
    $ mysql -u root -p -e "create database ogre character set = 'utf8';"
    $ ./manage.py create_db
    ```

4. TODO copy supervisor config

    ```bash
    # 
    ```

5. Create yourself a new user for OGRE:

    ```bash
    $ ./manage.py create_user <username> <password> <email_address>
    ```

6. You should then be able to view and log into the website at:

    ```bash
    http://127.0.0.1:8005/ogre
    ```

Troubleshooting
---------------


Hacking
-------

Hacking on OGRE involves just a little extra setup.


### Backend

You can install `watchdog` to monitor the code for changes and send a HUP to gunicorn as necessary.

In another shell session:

    ```bash
    pip install watchdog
    watchmedo shell-command --patterns="*.py" --recursive --command="kill -HUP `cat /tmp/gunicorn-ogre.pid`" .
    ```

Replace item 4 above with the following two steps:

1. Start gunicorn as a development server. You can modify the IP and port, then pass these to
   ogreclient when you're synchronising ebooks from the client.

    ```bash
    $ gunicorn ogreserver:app -c ogreserver/config/gunicorn.conf.py -b 127.0.0.1:8005
    ```

2. Start celeryd to process background tasks:

    ```bash
    $ celery worker --app=ogreserver
    ```

### Frontend

A couple extra prerequisites are necessary to start developing on ogre:

* aptitude install rubygems

The front end is built using [http://foundation.zurb.com/docs/index.html](Zurb's Foundation framework).

The sass version of the library can be installed like so:

    ```bash
    # gem install zurb-foundation
    # gem install compass
    ```

Then in another screen/tmux window or tab, set compass to watch the static directory:

    ```bash
    $ compass watch
    ```
