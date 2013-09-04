import argparse
import getpass
import json
import os
import subprocess
import sys
import tempfile

from core import doit


def entrypoint():
    # run some checks and create some config variables
    conf = prerequisites()

    parser = argparse.ArgumentParser(description="O.G.R.E. client application")
    parser.add_argument(
        '--ebook-home', '-H', action="store", dest="ebook_home",
        help=("The directory where you keep your ebooks. "
              "You can also set the environment variable $EBOOK_HOME"))
    parser.add_argument(
        '--ogreserver', action="store", dest="ogreserver",
        help="Override the default server host of oii.ogre.me.uk")
    parser.add_argument(
        '--username', '-u', action="store", dest="username",
        help=("Your O.G.R.E. username. "
              "You can also set the environment variable $EBOOK_USER"))
    parser.add_argument(
        '--password', '-p', action="store", dest="password",
        help=("Your O.G.R.E. password. "
              "You can also set the environment variable $EBOOK_PASS"))

    parser.add_argument(
        '--verbose', '-v', action="store_true", dest="verbose",
        help="Produce more output")
    parser.add_argument(
        '--quiet', '-q', action="store_true", dest="quiet",
        help="Don't produce any output")
    parser.add_argument(
        '--dry-run', '-d', action="store_true", dest="dry_run",
        help="Dry run the sync; don't actually upload anything to the server")

    args = parser.parse_args()

    ebook_home = args.ebook_home
    username = args.username
    password = args.password

    # setup the environment
    if ebook_home is None:
        ebook_home = os.getenv("EBOOK_HOME")
        if ebook_home is None or len(ebook_home) == 0:
            print "You must set the $EBOOK_HOME environment variable"
            sys.exit(1)

    if username is None:
        username = os.getenv("EBOOK_USER")
        if username is None or len(username) == 0:
            username = getpass.getuser()
            if username is not None:
                print "$EBOOK_USER is not set. Please enter your username, or press enter to use '%s':" % username
                ri = raw_input()
                if len(ri) > 0:
                    username = ri

        if username is None:
            print "$EBOOK_USER is not set. Please enter your username, or press enter to exit:"
            username = raw_input()
            if len(username) == 0:
                sys.exit(1)

    if password is None:
        password = os.getenv("EBOOK_PASS")
        if password is None or len(password) == 0:
            print "$EBOOK_PASS is not set. Please enter your password, or press enter to exit:"
            password = getpass.getpass()
            if len(password) == 0:
                sys.exit(1)

    doit(ebook_home, username, password,
        ogreserver=args.ogreserver,
        config_dir=conf['config_dir'],
        ebook_cache_path=conf['ebook_cache_path'],
        ebook_cache_temp_path=conf['ebook_cache_temp_path'],
        ebook_convert_path=conf['ebook_convert_path'],
        calibre_ebook_meta_bin=conf['calibre_ebook_meta_bin']
    )


def prerequisites():
    # setup some ebook cache file paths
    config_dir = "{0}/{1}".format(os.environ.get('XDG_CONFIG_HOME', os.path.expanduser('~/.config')), "ogre")
    ebook_cache_path = "{0}/ebook_cache".format(config_dir)
    ebook_cache_temp_path = "{0}/ebook_cache.tmp".format(config_dir)

    # setup a temp path for DRM checks with ebook-convert
    ebook_convert_path = "{0}/egg.epub".format(tempfile.gettempdir())

    # create a config directory in $HOME on first run
    if not os.path.exists(config_dir):
        print ("Please note that DRM scanning means the first run of ogreclient "
               "will be much slower than subsequent runs.")
        os.makedirs(config_dir)

        # locate calibre's binaries
        try:
            calibre_ebook_meta_bin = subprocess.check_output(
                ['find', '/Applications', '-type', 'f', '-name', 'ebook-meta']
            ).strip()

            if len(calibre_ebook_meta_bin) == 0:
                raise Exception
        except:
            sys.stderr.write("You must install calibre in order to use ogreclient.")
            sys.stderr.write("Please follow the simple instructions at http://ogre.oii.yt/install")
            sys.exit(1)

        conf = {
            'calibre_ebook_meta_bin': calibre_ebook_meta_bin
        }

        with open("{0}/app.config".format(config_dir), "w") as f_config:
            f_config.write(json.dumps(conf))

    else:
        # read in config from $HOME
        with open("{0}/app.config".format(config_dir), "r") as f_config:
            conf = json.loads(f_config.read())

    # return config object
    conf['config_dir'] = config_dir
    conf['ebook_cache_path'] = ebook_cache_path
    conf['ebook_cache_temp_path'] = ebook_cache_temp_path
    conf['ebook_convert_path'] = ebook_convert_path
    return conf