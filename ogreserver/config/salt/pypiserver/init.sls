pypiserver-virtualenv:
  virtualenv.managed:
    - name: /home/{{ pillar['app_user'] }}/.virtualenvs/pypiserver
    - requirements: salt://pypiserver/requirements.txt
    - runas: {{ pillar['app_user'] }}
    - require:
      - pip: virtualenv-init-distribute

pypiserver-log-dir:
  file.directory:
    - name: /var/log/pypiserver
    - mode: 755

pypiserver-package-dir:
  file.directory:
    - name: /var/pypiserver-cache
    - user: {{ pillar['app_user'] }}
    - mode: 755

pypiserver-etc-dir:
  file.directory:
    - name: /etc/pypiserver
    - mode: 755

# create a htpasswd file for package uploads
pypiserver-htpasswd:
  file.managed:
    - name: /tmp/htpasswd.py
    - source: salt://pypiserver/htpasswd.py
    - template: jinja
    - context:
        username: {{ pillar['app_name'] }}
        {% if pillar.get('pypiserver_password', None) %}
        password: {{ pillar['pypiserver_password'] }}
        {% endif %}
    - defaults:
        password: eggs
  cmd.wait:
    - name: /home/{{ pillar['app_user'] }}/.virtualenvs/pypiserver/bin/python /tmp/htpasswd.py
    - require:
      - virtualenv: pypiserver-virtualenv
      - file: pypiserver-etc-dir
    - watch:
      - file: pypiserver-htpasswd

pypiserver-supervisor-config:
  file.managed:
    - name: /etc/supervisor/conf.d/pypiserver.conf
    - source: salt://pypiserver/supervisord.conf
    - template: jinja
    - defaults:
        port: 8080
        package_dir: /var/pypiserver-cache
        runas: root
        overwrite: false
    - require:
      - virtualenv: pypiserver-virtualenv
      - file: pypiserver-log-dir
      - file: pypiserver-package-dir
    - require_in:
      - service: supervisor

pypiserver-supervisor-service:
  supervisord.running:
    - name: pypiserver
    - update: True
    - require:
      - service: supervisor
    - watch:
      - file: pypiserver-supervisor-config
