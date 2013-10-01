O.G.R.E.
========

OGRE is an ebook storage and synchronisation service.

OGRE comes in two parts:
  - a server built in Python relying on Flask and Celery
  - a cross-platform client script in Python which synchronises ebooks to the server.

OGRE is principally self-contained - you will just need some Amazon S3 credentials to get started.


Building with Salt
------------------

The ogreserver component is built of many components which operate togther in some semblance of harmony. For this reason, it's highly impractical to setup the project manually. Sticking with a pure Python solution, we opted for the gateway drug of [Salt](http://saltstack.com/) as our configuration management system.


Install with Vagrant
--------------------

These basic install instructions use Vagrant to quickly get an OGRE server running. If you've never setup a salty Vagrant box before, please refer to [this blog post](sdfds).

1. Get the Vagrant image. There are currently two hand-rolled Debian Wheezy builds provided, but you can of course use your own (we've tested with Debian/Ubuntu only).

Vagrant boxes:

- wget http://dl.dropbox.com/wheezy64uk.box
- wget http://dl.dropbox.com/wheezy64au.box

Commands:

    :::bash
    wget <a vagrant box>
    vagrant box add wheezy64 wheezy64uk.box

2. Clone this repo:

    :::bash
    git clone git@github.com:oii/ogre.git

3. Build a Vagrant VM:

    :::bash
    cd ogre/ogreserver/config/salty-vagrant
    vagrant up

4. Before building the server, you need to setup the Salt Pillar config file with your S3 credentials (and other optional things like github username, shell, location). The comments in the default config should be explanatory enough (pull requests welcome!):

    :::bash
    cp ../pillar/default_vars.sls ../pillar/dev_vars.sls
    vim ../pillar/dev_vars.sls

5. Add a github key

6. Now run highstate with Salt:

    vagrant ssh
    > sudo salt-call state.highstate

7. :

    :::bash
    http://127.0.0.1:8005/ogre

8. Now you'll want to synchronise some ebooks from Ogreclient.


Ogreclient
----------

This command is the baseline for you to first synchronise ebooks to your new ogreserver:

    :::bash
    python ogreclient --ogreserver 127.0.0.1:8005 -u mafro -p password -H /home/mafro/ebooks

The help for that command should make things more clear:

    :::bash
    usage: ogreclient [-h] [--ebook-home EBOOK_HOME] [--host HOST]
                    	[--username USERNAME] [--password PASSWORD] [--verbose]
                    	[--quiet] [--dry-run]

    O.G.R.E. client application

    optional arguments:
    	-h, --help            show this help message and exit
    	--ebook-home EBOOK_HOME, -H EBOOK_HOME
                            The directory where you keep your ebooks. You can also
                            set the environment variable $EBOOK_HOME
    	--host HOST           Override the default server host of oii.ogre.yt
    	--username USERNAME, -u USERNAME
                            Your O.G.R.E. username. You can also set the
                            environment variable $EBOOK_USER
    	--password PASSWORD, -p PASSWORD
                            Your O.G.R.E. password. You can also set the
                            environment variable $EBOOK_PASS
    	--verbose, -v         Produce lots of output
    	--quiet, -q           Don't produce any output
    	--dry-run, -d         Dry run the sync; don't actually upload anything to
                            the server


Sesame Config
-------------

You can add your recently minted dev config to the Git repo. Use sesame to encrypt and raise a pull request. 


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


Troubleshooting
---------------

If you have a problem, raise an issue or pull request with a problem/solution!
