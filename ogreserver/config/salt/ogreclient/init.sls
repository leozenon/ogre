include:
  - common
  - gitrepo
  - virtualenv-base
  - salt-hack

app-virtualenv:
  virtualenv.managed:
    - name: /home/{{ pillar['app_user'] }}/.virtualenvs/ogreclient
    - requirements: /srv/ogre/ogreclient/config/requirements.txt
    - runas: {{ pillar['app_user'] }}
    - require:
      - git: git-clone-app
