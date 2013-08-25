include:
  - common
  - compass
  - gitrepo
  - gunicorn
  - logs
  - mysql
  - nginx
  - rabbitmq
  - salt-hack
  - supervisor
  - virtualenv-base


extend:
  supervisor:
    pip.installed:
      - require:
        - file: /etc/supervisor/conf.d/gunicorn.ogreserver.conf
        - file: /etc/supervisor/conf.d/celeryd.ogreserver.conf
        - virtualenv: app-virtualenv
        - git: git-clone-app

  git-clone-app:
    git.latest:
      - rev: salt

  compass-supervisor-config:
    file.managed:
      - context:
          directory: /srv/ogre/ogreserver/static

  gunicorn-config:
    file.managed:
      - context:
          worker_class: gevent


pip-dependencies-extra:
  pkg.installed:
    - names:
      - libmysqlclient-dev
      - libevent-dev

app-virtualenv:
  virtualenv.managed:
    - name: /home/{{ pillar['app_user'] }}/.virtualenvs/{{ pillar['app_name'] }}
    - requirements: /srv/ogre/ogreserver/config/requirements.txt
    - pre_releases: true
    - runas: {{ pillar['app_user'] }}
    - require:
      - pip: virtualenv-init-distribute
      - pkg: pip-dependencies-extra
      - git: git-clone-app

flask-config:
  file.managed:
    - name: /srv/ogre/ogreserver/config/flask.app.conf.py
    - source: salt://ogreserver/flask.app.conf.py
    - template: jinja
    - user: {{ pillar['app_user'] }}
    - group: {{ pillar['app_user'] }}
    - require:
      - git: git-clone-app

ogre-init:
  cmd.run:
    - name: /home/{{ pillar['app_user'] }}/.virtualenvs/{{ pillar['app_name'] }}/bin/python manage.py init_ogre
    - cwd: /srv/ogre
    - unless: /home/{{ pillar['app_user'] }}/.virtualenvs/{{ pillar['app_name'] }}/bin/python manage.py init_ogre --test
    - user: {{ pillar['app_user'] }}
    - require:
      - virtualenv: app-virtualenv
      - file: flask-config
      - mysql_grants: create-mysql-user-perms


/etc/supervisor/conf.d/gunicorn.ogreserver.conf:
  file.managed:
    - source: salt://ogreserver/supervisord.gunicorn.conf
    - template: jinja

gunicorn-service:
  supervisord.running:
    - name: ogreserver.gunicorn
    - update: true
    - watch:
      - file: /etc/supervisor/conf.d/gunicorn.ogreserver.conf
      - file: /etc/gunicorn.d/{{ pillar['app_name'] }}.conf.py
    - require:
      - user: {{ pillar['app_user'] }}
      - file: flask-config
      - service: supervisor


/etc/supervisor/conf.d/celeryd.ogreserver.conf:
  file.managed:
    - source: salt://ogreserver/supervisord.celeryd.conf
    - template: jinja

celeryd-service:
  supervisord.running:
    - name: ogreserver.celeryd
    - update: true
    - watch:
      - file: /etc/supervisor/conf.d/celeryd.ogreserver.conf
    - require:
      - user: {{ pillar['app_user'] }}
      - file: flask-config
      - service: supervisor


#/etc/nginx/conf.d/upstream.conf:
#  file.managed:
#    - source: salt://app_server/upstream.conf
#    - require:
#      - pkg: nginx
#
#/etc/nginx/sites-available/app.basketchaser.com.conf:
#  file.managed:
#    - source: salt://app_server/app.basketchaser.com.conf.sls
#    - template: jinja
#    - require:
#      - pkg: nginx
#      - file: /etc/ssl/app.basketchaser.com.combined.crt
#      - file: /etc/ssl/app.basketchaser.com.key
#
#/etc/nginx/sites-enabled/app.basketchaser.com.conf:
#  file.symlink:
#    - target: /etc/nginx/sites-available/app.basketchaser.com.conf
#    - require:
#      - file: /etc/nginx/sites-available/app.basketchaser.com.conf
