#! /usr/bin/env python

from passlib.apache import HtpasswdFile

ht = HtpasswdFile("/etc/pypiserver/htpasswd", new=True)
ht.set_password("{{ username }}", "{{ password }}")
ht.save()
