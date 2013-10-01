import os


def url_for(name, filename=None):
    if filename is not None:
        if os.path.exists(os.path.join(name, filename)):
            return '/{0}'.format(os.path.join(name, filename))
    else:
        return '/{0}'.format(name)

def session():
    return "peanuts"

def get_flashed_messages():
    return []
