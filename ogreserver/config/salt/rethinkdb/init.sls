rethinkdb-pkgrepo:
  pkgrepo.managed:
    - humanname: RethinkDB PPA
    - name: deb http://ppa.launchpad.net/rethinkdb/ppa/ubuntu precise main
    - file: /etc/apt/sources.list.d/rethinkdb.list
    - keyid: 11D62AD6
    - keyserver: keyserver.ubuntu.com
    - require_in:
      - pkg: rethinkdb

rethinkdb:
  pkg.installed


python-pip-rethinkdb:
  pkg.installed:
    - name: python-pip

rethinkdb-python-driver:
  pip.installed:
    - name: rethinkdb
    - require:
      - pkg: python-pip-rethinkdb


rethinkdb-chown-lib:
  file.directory:
    - name: /var/lib/rethinkdb
    - user: rethinkdb
    - group: rethinkdb
    - require:
      - pkg: rethinkdb

rethinkdb-config:
  file.managed:
    - name: /etc/rethinkdb/instances.d/{{ pillar['app_name'] }}.conf
    - source: salt://rethinkdb/rethinkdb.instance.conf
    - template: jinja
    - user: rethinkdb
    - group: rethinkdb
    - defaults:
        app_name: {{ pillar['app_name'] }}
        production: true
    - require:
      - pkg: rethinkdb
  cmd.wait:
    - name: /etc/init.d/rethinkdb restart
    - require:
      - file: rethinkdb-chown-lib
    - watch:
      - file: rethinkdb-config
