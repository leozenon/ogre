gunicorn:
  pkg:
    - installed

/etc/gunicorn.d/{{ pillar['app_name'] }}.conf.py:
  file.managed:
    - source: salt://gunicorn/gunicorn.conf.py
    - template: jinja
    - mode: 644
    - context:
        app_name: {{ pillar['app_name'] }}
        gunicorn_port: {{ pillar['gunicorn_port'] }}
