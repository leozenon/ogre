import argparse
import getpass
import json
import os
import subprocess
import sys
import urllib

import core

from utils import capture
from utils import make_temp_directory
from utils import update_progress
from utils import CliPrinter


def entrypoint():
    parser = argparse.ArgumentParser(description="O.G.R.E. client application")
    parser.add_argument(
        '--ebook-home', '-H',
        help=("The directory where you keep your ebooks. "
              "You can also set the environment variable $EBOOK_HOME"))
    parser.add_argument(
        '--ogreserver',
        help="Override the default server host of oii.ogre.me.uk")
    parser.add_argument(
        '--username', '-u',
        help=("Your O.G.R.E. username. "
              "You can also set the environment variable $EBOOK_USER"))
    parser.add_argument(
        '--password', '-p',
        help=("Your O.G.R.E. password. "
              "You can also set the environment variable $EBOOK_PASS"))

    parser.add_argument(
        '--verbose', '-v', action="store_true",
        help="Produce lots of output")
    parser.add_argument(
        '--quiet', '-q', action="store_true",
        help="Don't produce any output")
    parser.add_argument(
        '--dry-run', '-d', action="store_true",
        help="Dry run the sync; don't actually upload anything to the server")

    args = parser.parse_args()

    if args.verbose and args.quiet:
        parser.error("You cannot specify --verbose and --quiet together!")

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

    # run some checks and create some config variables
    conf = prerequisites(args.host, username, password)

    # setup a temp path for DRM checks with ebook-convert
    with make_temp_directory() as ebook_convert_path:
        ret = core.doit(
            ebook_home=ebook_home,
            username=username,
            password=password,
            host=args.host,
            config_dir=conf['config_dir'],
            ebook_cache_path=conf['ebook_cache_path'],
            ebook_cache_temp_path=conf['ebook_cache_temp_path'],
            ebook_convert_path=ebook_convert_path,
            calibre_ebook_meta_bin=conf['calibre_ebook_meta_bin'],
            verbose=args.verbose,
            quiet=args.quiet,
        )

    # exit program
    if ret > 0:
        if ret == core.RETURN_CODES.error_auth:
            msg = "Something went wrong, contact tha spodz with..\nCode egg: {0}".format(core.last_error)
        elif ret == core.RETURN_CODES.error_bacon:
            msg = "Something went wrong, contact tha spodz with..\nCode bacon: {0}".format(core.last_error)
        elif ret == core.RETURN_CODES.error_mushroom:
            msg = "Something went wrong, contact tha spodz with..\nCode mushroom: {0}".format(core.last_error)
        elif ret == core.RETURN_CODES.error_spinach:
            msg = "Something went wrong, contact tha spodz with..\nCode spinach: {0}".format(core.last_error)
        elif ret == core.RETURN_CODES.auth_denied:
            msg = "Permission denied. This is a private system."
        elif ret == core.RETURN_CODES.no_ebooks:
            msg = "No ebooks found. Is $EBOOK_HOME set correctly?"
        elif ret == core.RETURN_CODES.no_uploads:
            msg = "Nothing to upload.."

        sys.stderr.write("{0}\n".format(msg))
        sys.exit(ret)


def prerequisites(ogreserver, username, password):
    # setup some ebook cache file paths
    config_dir = "{0}/{1}".format(os.environ.get('XDG_CONFIG_HOME', os.path.expanduser('~/.config')), "ogre")
    ebook_cache_path = "{0}/ebook_cache".format(config_dir)
    ebook_cache_temp_path = "{0}/ebook_cache.tmp".format(config_dir)

    prntr = CliPrinter(None)

    # use existing config if available
    if os.path.exists(config_dir) and os.path.exists("{0}/app.config".format(config_dir)):
        with open("{0}/app.config".format(config_dir), "r") as f_config:
            conf = json.loads(f_config.read())

    # create a config directory in $HOME on first run
    elif not os.path.exists(config_dir):
        prntr.p("Please note that DRM scanning means the first run of ogreclient "
                "will be much slower than subsequent runs.", notime=True)

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

    if ogreserver is None:
        ogreserver = core.OGRESERVER

    try:
        import dedrm
        prntr.p("Initialized DRM tools v{0}".format(dedrm.PLUGIN_VERSION))

        # extract the Kindle key
        kindlekeyfile = os.path.join(config_dir, 'kindlekey.k4i')
        if not os.path.exists(kindlekeyfile):
            import dedrm.kindlekey
            with capture() as out:
                dedrm.kindlekey.getkey(kindlekeyfile)

            for line in out:
                if 'K4PC' in line:
                    prntr.p("Extracted Kindle4PC key")
                    break
                elif 'k4Mac' in line:
                    prntr.p("Extracted Kindle4Mac key")
                    break

        # extract the Adobe key
        adeptkeyfile = os.path.join(config_dir, 'adeptkey.der')
        if not os.path.exists(adeptkeyfile):
            import dedrm.adobekey
            with capture() as out:
                dedrm.adobekey.getkey(adeptkeyfile)

            for line in out:
                if 'Saved a key' in line:
                    prntr.p("Extracted Adobe DE key")
                    break

    except ImportError:
        prntr.p("Downloading latest DRM tools")

        # retrieve the DRM tools
        session_key = core.authenticate(ogreserver, username, password)
        if type(session_key) is not str:
            prntr.p("Couldn't get DRM tools")
        else:
            urllib.urlretrieve(
                "http://{0}/download-dedrm/{1}".format(ogreserver, session_key),
                "/tmp/dedrm.tar.gz",
                dl_progress
            )

        # install DRM tools
        subprocess.check_output("pip install /tmp/dedrm.tar.gz", shell=True)

        try:
            import dedrm
            prntr.p("Initialized DRM tools v{0}".format(dedrm.PLUGIN_VERSION))
        except ImportError:
            prntr.e("Failed to download DRM tools. Please report this error.", notime=True)

    # return config object
    conf['config_dir'] = config_dir
    conf['ebook_cache_path'] = ebook_cache_path
    conf['ebook_cache_temp_path'] = ebook_cache_temp_path
    return conf


def dl_progress(count, size, total):
    progress = float(count * size) / float(total)
    update_progress(progress if progress < 1 else 1, length=core.PROGBAR_LEN)
