ssh-home-dir:
  file.directory:
    - name: /home/{{ pillar['app_user'] }}/.ssh
    - user: {{ pillar['app_user'] }}
    - group: {{ pillar['app_user'] }}
    - mode: 700
    - require:
      - user: create-app-user

ssh-config:
  file.managed:
    - name: /home/{{ pillar['app_user'] }}/.ssh/config
    - source: salt://ssh/ssh_config
    - user: {{ pillar['app_user'] }}
    - group: {{ pillar['app_user'] }}
    - mode: 600
    - require:
      - file: /home/{{ pillar['app_user'] }}/.ssh

github_known_hosts:
  ssh_known_hosts.present:
    - name: github.com
    - user: {{ pillar['app_user'] }}
    - fingerprint: 16:27:ac:a5:76:28:2d:36:63:1b:56:4d:eb:df:a6:48
    - require:
      - file: /home/{{ pillar['app_user'] }}/.ssh

github.pky:
  file.managed:
    - source: salt://{{ pillar['github_key_path'] }}
    - name: /home/{{ pillar['app_user'] }}/.ssh/github.pky
    - user: {{ pillar['app_user'] }}
    - group: {{ pillar['app_user'] }}
    - mode: 600
    - require:
      - file: /home/{{ pillar['app_user'] }}/.ssh/config
      - ssh_known_hosts: github_known_hosts
    - order: first
