include:
  - apt
  - create-app-user

pip-dependencies:
  pkg.latest:
    - names:
      - python-dev
      - build-essential
      - python-virtualenv
    - require:
      - file: apt-no-recommends
      - pkg: required-packages

virtualenvwrapper:
  pip.installed:
    - require:
      - pkg: pip-dependencies

virtualenv-init:
  virtualenv.managed:
    - name: /home/{{ pillar['app_user'] }}/.virtualenvs/{{ pillar['app_name'] }}
    - runas: {{ pillar['app_user'] }}
    - distribute: true
    - require:
      - pip: virtualenvwrapper
      - pkg: pip-dependencies
      - user: create-app-user

virtualenv-init-pip:
  pip.installed:
    - name: pip
    - upgrade: true
    - ignore_installed: true
    - user: {{ pillar['app_user'] }}
    - bin_env: /home/{{ pillar['app_user'] }}/.virtualenvs/{{ pillar['app_name'] }}
    - require:
      - virtualenv: virtualenv-init

virtualenv-init-distribute:
  pip.installed:
    - name: distribute
    - upgrade: true
    - ignore_installed: true
    - user: {{ pillar['app_user'] }}
    - bin_env: /home/{{ pillar['app_user'] }}/.virtualenvs/{{ pillar['app_name'] }}
    - require:
      - pip: virtualenv-init-pip
