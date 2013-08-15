create-app-user:
  group.present:
    - name: {{ pillar['app_user'] }}
  user.present:
    - name: {{ pillar['app_user'] }}
    - home: /home/{{ pillar['app_user'] }}
    - shell: /bin/bash
    - gid_from_name: true
    - require:
      - group: {{ pillar['app_user'] }}
    - order: first
