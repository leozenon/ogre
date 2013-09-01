#! /usr/bin/env python

from __future__ import (unicode_literals, division, absolute_import,
                        print_function)

__license__   = 'GPL v3'
__copyright__ = '2009, Kovid Goyal <kovid@kovidgoyal.net>'
__docformat__ = 'restructuredtext en'

import sys, os, shutil, subprocess, re, platform, time, signal, textwrap, tempfile, hashlib, errno

is64bit = platform.architecture()[0] == '64bit'
url = 'http://status.calibre-ebook.com/dist/linux'+('64' if is64bit else '32')
download_url = 'http://download.calibre-ebook.com/{0}/'
signature_url = 'http://calibre-ebook.com/downloads/signatures/%s.sha512'
url = os.environ.get('CALIBRE_INSTALLER_LOCAL_URL', url)
py3 = sys.version_info[0] > 2
enc = getattr(sys.stdout, 'encoding', 'UTF-8')
calibre_version = '{{ version }}'
urllib = __import__('urllib.request' if py3 else 'urllib', fromlist=1)
if py3:
    unicode = str
    raw_input = input

class TerminalController:
    BOL = ''             #: Move the cursor to the beginning of the line
    UP = ''              #: Move the cursor up one line
    DOWN = ''            #: Move the cursor down one line
    LEFT = ''            #: Move the cursor left one char
    RIGHT = ''           #: Move the cursor right one char

    # Deletion:
    CLEAR_SCREEN = ''    #: Clear the screen and move to home position
    CLEAR_EOL = ''       #: Clear to the end of the line.
    CLEAR_BOL = ''       #: Clear to the beginning of the line.
    CLEAR_EOS = ''       #: Clear to the end of the screen

    # Output modes:
    BOLD = ''            #: Turn on bold mode
    BLINK = ''           #: Turn on blink mode
    DIM = ''             #: Turn on half-bright mode
    REVERSE = ''         #: Turn on reverse-video mode
    NORMAL = ''          #: Turn off all modes

    # Cursor display:
    HIDE_CURSOR = ''     #: Make the cursor invisible
    SHOW_CURSOR = ''     #: Make the cursor visible

    # Terminal size:
    COLS = None          #: Width of the terminal (None for unknown)
    LINES = None         #: Height of the terminal (None for unknown)

    # Foreground colors:
    BLACK = BLUE = GREEN = CYAN = RED = MAGENTA = YELLOW = WHITE = ''

    # Background colors:
    BG_BLACK = BG_BLUE = BG_GREEN = BG_CYAN = ''
    BG_RED = BG_MAGENTA = BG_YELLOW = BG_WHITE = ''

    _STRING_CAPABILITIES = """
    BOL=cr UP=cuu1 DOWN=cud1 LEFT=cub1 RIGHT=cuf1
    CLEAR_SCREEN=clear CLEAR_EOL=el CLEAR_BOL=el1 CLEAR_EOS=ed BOLD=bold
    BLINK=blink DIM=dim REVERSE=rev UNDERLINE=smul NORMAL=sgr0
    HIDE_CURSOR=cinvis SHOW_CURSOR=cnorm""".split()
    _COLORS = """BLACK BLUE GREEN CYAN RED MAGENTA YELLOW WHITE""".split()
    _ANSICOLORS = "BLACK RED GREEN YELLOW BLUE MAGENTA CYAN WHITE".split()

    def __init__(self, term_stream=sys.stdout):
        # Curses isn't available on all platforms
        try: import curses
        except: return

        # If the stream isn't a tty, then assume it has no capabilities.
        if not hasattr(term_stream, 'isatty') or not term_stream.isatty(): return

        # Check the terminal type.  If we fail, then assume that the
        # terminal has no capabilities.
        try: curses.setupterm()
        except: return

        # Look up numeric capabilities.
        self.COLS = curses.tigetnum('cols')
        self.LINES = curses.tigetnum('lines')

        # Look up string capabilities.
        for capability in self._STRING_CAPABILITIES:
            (attrib, cap_name) = capability.split('=')
            setattr(self, attrib, self._escape_code(self._tigetstr(cap_name)))

        # Colors
        set_fg = self._tigetstr('setf')
        if set_fg:
            if not isinstance(set_fg, bytes):
                set_fg = set_fg.encode('utf-8')
            for i,color in zip(range(len(self._COLORS)), self._COLORS):
                setattr(self, color,
                        self._escape_code(curses.tparm((set_fg), i)))
        set_fg_ansi = self._tigetstr('setaf')
        if set_fg_ansi:
            if not isinstance(set_fg_ansi, bytes):
                set_fg_ansi = set_fg_ansi.encode('utf-8')
            for i,color in zip(range(len(self._ANSICOLORS)), self._ANSICOLORS):
                setattr(self, color,
                        self._escape_code(curses.tparm((set_fg_ansi),
                            i)))
        set_bg = self._tigetstr('setb')
        if set_bg:
            if not isinstance(set_bg, bytes):
                set_bg = set_bg.encode('utf-8')
            for i,color in zip(range(len(self._COLORS)), self._COLORS):
                setattr(self, 'BG_'+color,
                        self._escape_code(curses.tparm((set_bg), i)))
        set_bg_ansi = self._tigetstr('setab')
        if set_bg_ansi:
            if not isinstance(set_bg_ansi, bytes):
                set_bg_ansi = set_bg_ansi.encode('utf-8')
            for i,color in zip(range(len(self._ANSICOLORS)), self._ANSICOLORS):
                setattr(self, 'BG_'+color,
                        self._escape_code(curses.tparm((set_bg_ansi),
                            i)))

    def _escape_code(self, raw):
        if not raw:
            raw = ''
        if not isinstance(raw, unicode):
            raw = raw.decode('ascii')
        return raw

    def _tigetstr(self, cap_name):
        # String capabilities can include "delays" of the form "$<2>".
        # For any modern terminal, we should be able to just ignore
        # these, so strip them out.
        import curses
        if isinstance(cap_name, bytes):
            cap_name = cap_name.decode('utf-8')
        cap = self._escape_code(curses.tigetstr(cap_name))
        return re.sub(r'\$<\d+>[/*]?', b'', cap)

    def render(self, template):
        return re.sub(r'\$\$|\${\w+}', self._render_sub, template)

    def _render_sub(self, match):
        s = match.group()
        if s == '$$': return s
        else: return getattr(self, s[2:-1])

class ProgressBar:
    BAR = '%3d%% ${GREEN}[${BOLD}%s%s${NORMAL}${GREEN}]${NORMAL}\n'
    HEADER = '${BOLD}${CYAN}%s${NORMAL}\n\n'

    def __init__(self, term, header):
        self.term = term
        if not (self.term.CLEAR_EOL and self.term.UP and self.term.BOL):
            raise ValueError("Terminal isn't capable enough -- you "
            "should use a simpler progress display.")
        self.width = self.term.COLS or 75
        self.bar = term.render(self.BAR)
        self.header = self.term.render(self.HEADER % header.center(self.width))
        self.cleared = 1 #: true if we haven't drawn the bar yet.

    def update(self, percent, message=''):
        out = (sys.stdout.buffer if py3 else sys.stdout)
        if self.cleared:
            out.write(self.header.encode(enc))
            self.cleared = 0
        n = int((self.width-10)*percent)
        msg = message.center(self.width)
        msg = (self.term.BOL + self.term.UP + self.term.CLEAR_EOL +
            (self.bar % (100*percent, '='*n, '-'*(self.width-10-n))) +
            self.term.CLEAR_EOL + msg).encode(enc)
        out.write(msg)
        out.flush()

    def clear(self):
        out = (sys.stdout.buffer if py3 else sys.stdout)
        if not self.cleared:
            out.write((self.term.BOL + self.term.CLEAR_EOL +
            self.term.UP + self.term.CLEAR_EOL +
            self.term.UP + self.term.CLEAR_EOL).encode(enc))
            self.cleared = 1
            out.flush()

def prints(*args, **kwargs):
    return
#    f = kwargs.get('file', sys.stdout.buffer if py3 else sys.stdout)
#    end = kwargs.get('end', b'\n')
#    enc = getattr(f, 'encoding', 'utf-8')
#
#    if isinstance(end, unicode):
#        end = end.encode(enc)
#    for x in args:
#        if isinstance(x, unicode):
#            x = x.encode(enc)
#        f.write(x)
#        f.write(b' ')
#    f.write(end)
#    if py3 and f is sys.stdout.buffer:
#        f.flush()

class Reporter:

    def __init__(self, fname):
        try:
            self.pb  = ProgressBar(TerminalController(), 'Downloading '+fname)
        except ValueError:
            prints('Downloading', fname)
            self.pb = None

    def __call__(self, blocks, block_size, total_size):
        percent = (blocks*block_size)/float(total_size)
        if self.pb is None:
            prints('Downloaded {0:%}'.format(percent))
        else:
            try:
                self.pb.update(percent)
            except:
                import traceback
                traceback.print_exc()

# Downloading

def clean_cache(cache, fname):
    for x in os.listdir(cache):
        if fname not in x:
            os.remove(os.path.join(cache, x))

def check_signature(dest, signature):
    if not os.path.exists(dest):
        return False
    m = hashlib.sha512()
    with open(dest, 'rb') as f:
        raw = True
        while raw:
            raw = f.read(1024*1024)
            m.update(raw)
    print('dest {0}'.format(dest))
    print(' > {0}'.format(m.hexdigest().encode('ascii')))
    return m.hexdigest().encode('ascii') == signature

class URLOpener(urllib.FancyURLopener):

    def http_error_206(self, url, fp, errcode, errmsg, headers, data=None):
        ''' 206 means partial content, ignore it '''
        pass

def do_download(dest, fname):
    prints('Will download and install', os.path.basename(dest))
    reporter = Reporter(os.path.basename(dest))
    offset = 0
    urlopener = URLOpener()
    if os.path.exists(dest):
        offset = os.path.getsize(dest)

    # Get content length and check if range is supported
    rurl = download_url.format(calibre_version)+fname
    rq = urllib.urlopen(rurl)
    headers = rq.info()
    size = int(headers['content-length'])
    accepts_ranges = headers.get('accept-ranges', None) == 'bytes'
    mode = 'wb'
    if accepts_ranges and offset > 0:
        mode = 'ab'
        rq.close()
        urlopener.addheader('Range', 'bytes=%s-'%offset)
        rq = urlopener.open(rurl)
    print('url {0}'.format(rq.geturl()))
    with open(dest, mode) as f:
        while f.tell() < size:
            raw = rq.read(8192)
            if not raw:
                break
            f.write(raw)
            reporter(f.tell(), 1, size)
    rq.close()
    if os.path.getsize(dest) < size:
        print ('Download failed, try again later')
        raise SystemExit(1)
    prints('Downloaded %s bytes'%os.path.getsize(dest))

def download_tarball():
    fname = 'calibre-%s-i686.tar.bz2'%calibre_version
    if is64bit:
        fname = fname.replace('i686', 'x86_64')
    signature = urllib.urlopen(signature_url%fname).read()
    print('version {0}'.format(calibre_version))
    print('sigurl {0}'.format(signature_url%fname))
    print(' > {0}'.format(signature))
    tdir = tempfile.gettempdir()
    cache = os.path.join(tdir, 'calibre-installer-cache')
    if not os.path.exists(cache):
        os.makedirs(cache)
    clean_cache(cache, fname)
    dest = os.path.join(cache, fname)
    if check_signature(dest, signature):
        print ('Using previously downloaded', fname)
        return dest
    cached_sigf = dest +'.signature'
    cached_sig = None
    if os.path.exists(cached_sigf):
        with open(cached_sigf, 'rb') as sigf:
            cached_sig = sigf.read()
    if cached_sig != signature and os.path.exists(dest):
        os.remove(dest)
    try:
        with open(cached_sigf, 'wb') as f:
            f.write(signature)
    except IOError as e:
        if e.errno != errno.EACCES:
            raise
        print ('The installer cache directory has incorrect permissions.'
                ' Delete %s and try again.'%cache)
        raise SystemExit(1)
    do_download(dest, fname)
    prints('Checking downloaded file integrity...')
    if not check_signature(dest, signature):
        os.remove(dest)
        print ('The downloaded files\' hash does not match. '
                'Try the download again later.')
        raise SystemExit(1)
    return dest

def extract_tarball(tar, destdir):
    prints('Extracting application files...')
    if hasattr(tar, 'read'):
        tar = tar.name
    with open('/dev/null', 'w') as null:
        subprocess.check_call(['tar', 'xjof', tar, '-C', destdir], stdout=null,
            preexec_fn=lambda:
                        signal.signal(signal.SIGPIPE, signal.SIG_DFL))

def download_and_extract(destdir):
    try:
        f = download_tarball()
    except:
        raise
        print('Failed to download, retrying in 30 seconds...')
        time.sleep(30)
        try:
            f = download_tarball()
        except:
            print('Failed to download, aborting')
            sys.exit(1)

    if os.path.exists(destdir):
        shutil.rmtree(destdir)
    os.makedirs(destdir)

    print('Extracting files to %s ...'%destdir)
    extract_tarball(f, destdir)

def main(install_dir=None, bin_dir=None, share_dir=None):
    defdir = '/opt'
    autodir = os.environ.get('CALIBRE_INSTALL_DIR', install_dir)
    automated = False
    if (autodir is None or not os.path.exists(autodir) or not
            os.path.isdir(autodir)):
        destdir = raw_input('Enter the installation directory for calibre [%s]: '%defdir).strip()
    else:
        automated = True
        prints('Automatically installing to: %s' % autodir)
        destdir = autodir
    if not destdir:
        destdir = defdir
    destdir = os.path.abspath(destdir)
    if destdir == '/usr/bin':
        prints(destdir, 'is not a valid install location. Choose', end='')
        prints('a location like /opt or /usr/local')
        return 1
    destdir = os.path.join(destdir, 'calibre')
    if os.path.exists(destdir):
        if not os.path.isdir(destdir):
            prints(destdir, 'exists and is not a directory. Choose a location like /opt or /usr/local')
            return 1

    download_and_extract(destdir)

    pi = [os.path.join(destdir, 'calibre_postinstall')]
    if bin_dir is not None:
        pi.extend(['--bindir', bin_dir])
    if share_dir is not None:
        pi.extend(['--sharedir', share_dir])
    subprocess.call(pi, shell=len(pi) == 1)
    if not automated:
        prints()
        prints(textwrap.dedent(
            '''
            You can automate future calibre installs by specifying the
            installation directory in the install command itself, like
            this:

            sudo python -c "import sys; py3 = sys.version_info[0] > 2; u = __import__('urllib.request' if py3 else 'urllib', fromlist=1); exec(u.urlopen('http://status.calibre-ebook.com/linux_installer').read()); main(install_dir='/opt')"

            Change /opt above to whatever directory you want calibre to be
            automatically installed to
            '''))
        prints()
    prints('Run "calibre" to start calibre')
    return 0

if __name__ == "__main__":
    main(install_dir='/opt')
