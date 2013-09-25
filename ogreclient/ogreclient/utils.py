import base64
import contextlib
import datetime
import hashlib
import random
import shutil
import string
import sys
import tempfile


def compute_md5(filepath, buf_size=8192):
    """
    Adapted from boto/utils.py

    Compute MD5 hash on passed file and return results in a tuple of values.

    :type fp: file
    :param fp: File pointer to the file to MD5 hash.  The file pointer
               will be reset to the beginning of the file before the
               method returns.

    :type buf_size: integer
    :param buf_size: Number of bytes per read request.

    :rtype: tuple
    :return: A tuple containing the hex digest version of the MD5 hash
             as the first element, the base64 encoded version of the
             plain digest as the second element and the file size as
             the third element.
    """
    fp = open(filepath, "rb")
    try:
        m = hashlib.md5()
        fp.seek(0)
        s = fp.read(buf_size)
        while s:
            m.update(s)
            s = fp.read(buf_size)

        hex_md5 = m.hexdigest()
        base64md5 = base64.encodestring(m.digest())

        if base64md5[-1] == '\n':
            base64md5 = base64md5[0:-1]

        file_size = fp.tell()
        fp.seek(0)
        return (hex_md5, base64md5, file_size)

    finally:
        fp.close()


@contextlib.contextmanager
def make_temp_directory():
    temp_dir = tempfile.mkdtemp()
    try:
        yield temp_dir
    except Exception as e:
        raise e
    finally:
        shutil.rmtree(temp_dir)


def id_generator(size=6, chars=string.ascii_uppercase + string.digits):
    return ''.join(random.choice(chars) for x in range(size))


def update_progress(p, length=30):
    i = round(p * 100, 1)
    sys.stdout.write("\r[{0}{1}] {2}%".format("#" * int(p * length), " " * (length - int(p * length)), i))


@contextlib.contextmanager
def capture():
    import sys, codecs
    from cStringIO import StringIO
    oldout, olderr = sys.stdout, sys.stderr
    try:
        out = [
            codecs.getwriter("utf8")(StringIO()),
            codecs.getwriter("utf8")(StringIO()),
        ]
        sys.stdout, sys.stderr = out
        yield out
    finally:
        sys.stdout, sys.stderr = oldout, olderr
        out[0] = out[0].getvalue()
        out[1] = out[1].getvalue()


class CliPrinter:
    WHITE = '\033[97m'
    CYAN = '\033[96m'
    MAGENTA = '\033[95m'
    BLUE = '\033[94m'
    YELLOW = '\033[93m'
    GREEN = '\033[92m'
    RED = '\033[91m'
    GREY = '\033[90m'
    END = '\033[0m'

    ERROR = 'ERROR'
    DEBUG = 'DEBUG'
    UNKNOWN = 'UNKNOWN'
    DEDRM = 'DEDRM'
    WRONG_KEY = 'WRONG KEY'
    CORRUPT = 'CORRUPT'
    NONE = 'NONE'
    RESPONSE = 'RESPONSE'

    def __init__(self, start, quiet=False):
        self.start = start
        self.quiet = quiet
        self.progress_running = False
        self.nonl_mode = False

    def _get_colour_and_prefix(self, mode=None, success=None):
        colour = self.WHITE

        if mode == self.UNKNOWN:
            colour = self.BLUE
        elif mode == self.DEDRM:
            colour = self.GREEN
            if success is True:
                prefix = 'DECRYPTED'

        if mode == self.ERROR:
            prefix = 'ERROR'
            colour = self.RED
        elif mode is None:
            prefix = 'OGRECLIENT'
        else:
            prefix = mode

        if success is True:
            colour = self.GREEN
        elif success is False:
            colour = self.RED
            if prefix is None:
                prefix = 'ERROR'

        return colour, prefix

    def e(self, msg, mode=ERROR, excp=None):
        self.p(msg, mode, success=False, extra="{0}: {1}".format(excp.__class__.__name__, excp))

    def p(self, msg, mode=None, notime=False, success=None, extra=None, nonl=False):
        if self.quiet is True:
            return

        if self.line_needs_finishing is True:
            self.line_needs_finishing = False
            sys.stdout.write('{0}\n'.format(msg))
            return

        if self.progress_running is True:
            self.progress_running = False
            sys.stdout.write('\n')

        colour, prefix = self._get_colour_and_prefix(mode, success=success)

        out = sys.stdout

        if success is False:
            out = sys.stderr

        if notime is True:
            out.write('{0}[{1: <10}]      {2}{3}{4}'.format(
                CliPrinter.YELLOW, prefix, colour, msg, CliPrinter.END
            ))
        else:
            t = (datetime.datetime.now() - self.start).seconds
            out.write('{0}[{1: <10}]{2} {3: >4} {4}{5}{6}'.format(
                CliPrinter.YELLOW, prefix, CliPrinter.GREY, t, colour, msg, CliPrinter.END
            ))

        if extra is not None:
            out.write('{0}[{1: <10}]      {2}> {3}{4}'.format(
                CliPrinter.YELLOW, prefix, CliPrinter.WHITE, CliPrinter.END, extra
            ))

        if nonl is True:
            self.line_needs_finishing = True
        else:
            out.write('\n')

    def progress(self, amount, mode):
        if self.quiet is True:
            return

        self.progress_running = True
        colour, prefix = self._get_colour_and_prefix(mode)

        t = (datetime.datetime.now() - self.start).seconds
        sys.stdout.write('\r{0}[{1: <10}]{2} {3: >4} {4}{5}{6}'.format(
            CliPrinter.YELLOW, prefix, CliPrinter.GREY, t, colour, (amount * '#'), CliPrinter.END
        ))
        sys.stdout.flush()


def enum(*sequential, **named):
    enums = dict(zip(sequential, range(len(sequential))), **named)
    return type('Enum', (), enums)
