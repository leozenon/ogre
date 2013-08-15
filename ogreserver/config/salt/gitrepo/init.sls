include:
  - create-app-user
  - ssh

/srv/{{ pillar['project_name'] }}:
  file.directory:
    - user: {{ pillar['app_user'] }}
    - group: {{ pillar['app_user'] }}
    - makedirs: true
    - require:
      - user: create-app-user

/home/{{ pillar['login_user'] }}/.gitconfig:
  file.managed:
    - source: salt://gitrepo/gitconfig
    - replace: false
    - template: jinja
    - mode: 644

git-clone-app:
  git.latest:
    - name: git@github.com:oii/ogre.git
    - rev: develop
    - target: /srv/{{ pillar['project_name'] }}
    - runas: {{ pillar['app_user'] }}
    - require:
      - pkg: git
      - file: github.pky
      - file: /srv/ogre
