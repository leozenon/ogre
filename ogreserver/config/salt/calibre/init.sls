calibre-install:
  file.managed:
    - name: /opt/calibre_installer.py
    - source: salt://calibre/linux_installer.py
    - template: jinja
    - mode: 744
    - context:
        version: 1.4.0
  cmd.wait:
    - name: /opt/calibre_installer.py
    - watch:
      - file: calibre-install
