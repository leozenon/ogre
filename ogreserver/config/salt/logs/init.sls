include:
  - create-app-user

app-log-directory:
  file.directory:
    - name: /var/log/{{ pillar['app_name'] }}
    - user: {{ pillar['app_user'] }}
    - group: {{ pillar['app_user'] }}
    - mode: 755
    - recurse:
      - user
      - group
    - require:
      - user: {{ pillar['app_user'] }}

app-logrotate-crontab:
  file.managed:
    - name: /etc/logrotate.d/{{ pillar['app_name'] }}
    - source: salt://logs/logrotate.conf
    - mode: 644
    - template: jinja
    - context:
        owner: {{ pillar['app_user'] }}
