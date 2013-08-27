include:
  - watchdog

extend:
  gunicorn-config:
    file.managed:
      - context:
          bind_hostname: "0.0.0.0"
          gunicorn_port: {{ pillar['gunicorn_port'] }}
          worker_class: sync
          timeout: 300
          loglevel: info

  supervisor-config:
    file.managed:
      - context:
          runas: {{ pillar['login_user'] }}

  supervisor-log-dir:
    file.directory:
      - user: {{ pillar['login_user'] }}

  supervisor-sock-dir:
    file.directory:
      - user: {{ pillar['login_user'] }}

  supervisor-init-script:
    file.managed:
      - user: {{ pillar['login_user'] }}

  tmux-powerline-theme:
    file.managed:
      - context:
          gunicorn: true
          celeryd: true

  rethinkdb-config:
    file.managed:
      - context:
          production: false


logs-chown:
  file.directory:
    - name: /var/log/{{ pillar['app_name'] }}
    - recurse:
      - user
      - group
    - user: {{ pillar['login_user'] }}
    - group: {{ pillar['login_user'] }}
    - require:
      - supervisord: gunicorn-service
      - supervisord: celeryd-service

ogre-create-user:
  cmd.run:
    - name: /home/{{ pillar['app_user'] }}/.virtualenvs/{{ pillar['app_name'] }}/bin/python manage.py create_user {{ pillar['ogre_user_name'] }} {{ pillar['ogre_user_pass'] }} {{ pillar['ogre_user_email'] }}
    - unless: /home/{{ pillar['app_user'] }}/.virtualenvs/{{ pillar['app_name'] }}/bin/python manage.py create_user {{ pillar['ogre_user_name'] }} null null --test
    - cwd: /srv/ogre
    - user: {{ pillar['app_user'] }}
    - require:
      - virtualenv: app-virtualenv
      - cmd: ogre-init

rubygems:
  pkg.installed

zurb-foundation-gem:
  gem.installed:
    - name: zurb-foundation
    - require:
      - pkg: rubygems

# install tmux segments for gunicorn & celeryd state
{% for app in ('gunicorn', 'celeryd') %}
tmux-{{ app }}-segment:
  file.managed:
    - name: /home/{{ pillar['login_user'] }}/tmux-powerline/segments/{{ app }}.sh
    - source: salt://tmux/pid-segment.tmpl.sh
    - template: jinja
    - user: {{ pillar['login_user'] }}
    - context:
        component_name: {{ app }}
    - require:
      - cmd: dotfiles-install-tmux
      - git: tmux-powerline-install
{% endfor %}
