gcd-dependencies:
  pkg.installed:
    - names:
      - openjdk-7-jre-headless
      - unzip

gcd-download:
  file.managed:
    - name: /home/{{ pillar['login_user'] }}/gcd-v1beta1-rev2-1.0.1.zip
    - source: http://commondatastorage.googleapis.com/gcd/tools/gcd-v1beta1-rev2-1.0.1.zip
    - source_hash: sha1=c37290e20be3ceb8b0720c775758c96802c16651
    - user: {{ pillar['login_user'] }}
    - group: {{ pillar['login_user'] }}
  cmd.wait:
    - name: unzip gcd-v1beta1-rev2-1.0.1.zip
    - cwd: /home/{{ pillar['login_user'] }}
    - user: {{ pillar['login_user'] }}
    - watch:
      - file: gcd-download
    - require:
      - pkg: gcd-dependencies

gcd-create-datastore:
  cmd.run:
    - name: echo {{ pillar['app_name'] }} | ./gcd.sh create {{ pillar['app_name'] }}
    - cwd: /home/{{ pillar['login_user'] }}/gcd-v1beta1-rev2-1.0.1
    - unless: test -d /home/{{ pillar['login_user'] }}/gcd-v1beta1-rev2-1.0.1/{{ pillar['app_name'] }}
    - require:
      - pkg: gcd-dependencies
      - cmd: gcd-download

gcd-supervisor-config:
  file.managed:
    - name: /etc/supervisor/conf.d/gcd.{{ pillar['app_name'] }}.conf
    - source: salt://googledatastore/supervisord.conf
    - template: jinja
    - context:
        directory: /home/{{ pillar['app_user'] }}/gcd-v1beta1-rev2-1.0.1
    - require:
      - cmd: gcd-create-datastore
    - require_in:
      - service: supervisor

gcd-supervisor-service:
  supervisord.running:
    - name: {{ pillar['app_name'] }}.gcd
    - update: True
    - require:
      - service: supervisor
    - watch:
      - file: gcd-supervisor-config
