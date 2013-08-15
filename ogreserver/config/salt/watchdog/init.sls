watchdog:
  pip.installed:
    - user: {{ pillar['app_user'] }}
    - bin_env: /home/{{ pillar['app_user'] }}/.virtualenvs/{{ pillar['app_name'] }}

watchdog-supervisor-config:
  file.managed:
    - name: /etc/supervisor/conf.d/watchdog.{{ pillar['app_name'] }}.conf
    - source: salt://watchdog/supervisord.conf
    - template: jinja
    - context:
        directory: /srv/{{ pillar['project_name'] }}/{{ pillar['app_name'] }}
        venv: /home/{{ pillar['app_user'] }}/.virtualenvs/{{ pillar['app_name'] }}
        app_name: {{ pillar['app_name'] }}
        watch_name: gunicorn
        patterns: "*.py"
        command: "kill -HUP `cat /tmp/gunicorn-{{ pillar['app_name'] }}.pid`"
        user: {{ pillar['app_user'] }}
    - require:
      - pip: watchdog

watchdog-supervisor-service:
  supervisord.running:
    - name: {{ pillar['app_name'] }}.gunicorn.watchdog
    - update: true
    - require:
      - pip: watchdog
      - supervisord: gunicorn-service
    - watch:
      - file: watchdog-supervisor-config
