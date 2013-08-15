vim:
  pkg.installed

/home/{{ pillar['login_user'] }}/.vimrc:
  file.managed:
    - source: salt://vim/vimrc
    - replace: false
    - user: {{ pillar['login_user'] }}
    - group: {{ pillar['login_user'] }}

/home/{{ pillar['login_user'] }}/.vim:
  file.recurse:
    - source: salt://vim/vim
    - user: {{ pillar['login_user'] }}
    - group: {{ pillar['login_user'] }}
