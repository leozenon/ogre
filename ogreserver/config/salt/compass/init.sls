compass-rubygems:
  pkg.installed:
    - name: rubygems

compass-gem:
  gem.installed:
    - name: compass
    - require:
      - pkg: rubygems

compass-supervisor-config:
  file.managed:
    - name: /etc/supervisor/conf.d/compass.{{ pillar['app_name'] }}.conf
    - source: salt://compass/supervisord.conf
    - template: jinja
    - default:
        directory: /srv/{{ pillar['app_name'] }}

compass-supervisor-service:
  supervisord.running:
    - name: {{ pillar['app_name'] }}.compass
    - update: true
    - require:
      - gem: compass-gem
    - watch:
      - file: compass-supervisor-config
