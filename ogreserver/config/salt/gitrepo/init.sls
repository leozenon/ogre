include:
  - ssh

/srv/{{ pillar['project_name'] }}:
  file.directory:
    - user: {{ pillar['app_user'] }}
    - group: {{ pillar['app_user'] }}
    - makedirs: true

/home/{{ pillar['login_user'] }}/.gitconfig:
  file.managed:
    - source: salt://gitrepo/gitconfig
    - user: {{ pillar['login_user'] }}
    - group: {{ pillar['login_user'] }}
    - onlyif: test -f /home/{{ pillar['login_user'] }}/.gitconfig
    - template: jinja
    - mode: 644
    - replace: false

git-clone-app:
  git.latest:
    - name: git@github.com:oii/ogre.git
    - rev: develop
    - target: /srv/{{ pillar['project_name'] }}
    - user: {{ pillar['app_user'] }}
    - require:
      - pkg: git
      - file: github.pky
      - file: /srv/ogre
