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


Ogreserver
----------

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
    mkvirtualenv ogre
    pip install -r config/requirements.txt
    ```

    On OSX you might get an error when compiling `gevent`. In order to fix this install Xcode 4.4+
	and install the command line tools http://stackoverflow.com/q/11716107/425050.

3. Setup the mysql app database. The optional second mysql command will create a new
user for OGRE; which will subsequently be used in the SQLALCHEMY_DATABASE_URI config var:

    ```bash
    mysql -u root -p -e "create database ogre character set utf8;"
    mysql -u root -p -e "GRANT SELECT,INSERT,UPDATE,DELETE,CREATE,ALTER,INDEX,DROP,LOCK TABLES ON ogre.* TO 'db_username'@'localhost' IDENTIFIED BY 'password';"
    ```

4. Initialize your OGRE SDB bucket, S3 storage and local mysql DB:

    ```bash
    ./manage.py init_ogre
    ```

5. Create yourself a new user for OGRE:

    ```bash
    ./manage.py create_user <username> <password> <email_address>
    ```

6. Modify the supervisor config. You will be looking to replace all paths in this 
file with ones that match your setup. Then run the following:

    ```bash
    ln -s /path/to/project/ogreserver/supervisor.conf /etc/supervisor/conf.d/ogre.conf
    sudo supervisorctl update
    ```

7. You should then be able to view and log into the website at:

    ```bash
    http://127.0.0.1:8005/ogre
    ```

8. Now you'll want to synchronise some ebooks from Ogreclient.


Ogreclient
----------

This command is the baseline for you to first synchronise ebooks to your new ogreserver:

```bash
python ogreclient --ogreserver 127.0.0.1:8005 -u mafro -p password -H /home/mafro/ebooks
```

The help for that command should make things more clear:

```bash
python ogreclient -h
usage: ogreclient [-h] [--ebook-home EBOOK_HOME] [--ogreserver OGRESERVER]
                  [--username USERNAME] [--password PASSWORD] [--verbose]
                  [--quiet] [--dry-run]

O.G.R.E. client application

optional arguments:
  -h, --help            show this help message and exit
  --ebook-home EBOOK_HOME, -H EBOOK_HOME
                        The directory where you keep your ebooks. You can also
                        set the environment variable $EBOOK_HOME
  --ogreserver OGRESERVER
                        Override the default server host of oii.ogre.me.uk
  --username USERNAME, -u USERNAME
                        Your O.G.R.E. username. You can also set the
                        environment variable $EBOOK_USER
  --password PASSWORD, -p PASSWORD
                        Your O.G.R.E. password. You can also set the
                        environment variable $EBOOK_PASS
  --verbose, -v         Produce more output
  --quiet, -q           Don't produce any output
  --dry-run, -d         Dry run the sync; don't actually upload anything to
                        the server
```

Troubleshooting
---------------


Hacking
-------

Hacking on OGRE involves just a little extra setup.


### Backend

Replace step `4` above with the following two steps:

1. Start gunicorn as a development server. You can modify the IP and port, then pass these to
   ogreclient when you're synchronising ebooks from the client.

    ```bash
    gunicorn ogreserver:app -c ogreserver/config/gunicorn.conf.py -b 127.0.0.1:8005
    ```

2. Start celeryd to process background tasks:

    ```bash
    celery worker --app=ogreserver
    ```

## Debugging

When debugging the server code running gunicorn, it's useful to enter the debugger inline with `pdb`.
Drop this into your code:

```python
import pdb; pdb.set_trace()
```

In order to do this, you will need to start gunicorn in worker `sync` mode, to prevent our connection 
timing out whilst we are in the debugger. It's also pertinent to set a high worker timeout.

```bash
gunicorn ogreserver:app -c ogreserver/config/gunicorn.conf.py -b 127.0.0.1:8005 -k sync -t 300
```

# Polling for code changes

You can install `watchdog` to monitor the code for changes and send a HUP to gunicorn as necessary.

In another shell session:

```bash
pip install watchdog
watchmedo shell-command --patterns="*.py" --recursive --command="kill -HUP `cat /tmp/gunicorn-ogre.pid`" .
```


### Frontend

A couple extra prerequisites are necessary to start developing on ogre:

```bash
aptitude install rubygems
```

The front end is built using [http://foundation.zurb.com/docs/index.html](Zurb's Foundation framework).

The sass version of the library can be installed like so:

```bash
gem install zurb-foundation
gem install compass
```

Then in another screen/tmux window or tab, set compass to watch the static directory:

```bash
compass watch ogreserver/static
```
