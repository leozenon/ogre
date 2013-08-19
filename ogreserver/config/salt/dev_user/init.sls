include:
  - gitrepo
  - ssh

dev_packages:
  pkg.installed:
    - names:
      - curl
      - man-db
      - telnet

# install some extra packages
{% for package_name in pillar.get('extras', []) %}
extra_{{ package_name }}:
  pkg.installed:
    - name: {{ package_name }}
{% endfor %}

# set the default shell
modify-login-user:
  user.present:
    - name: {{ pillar['login_user'] }}
    - shell: /bin/{{ pillar['shell'] }}
    - unless: getent passwd $LOGNAME | grep {{ pillar['shell'] }}

# grab the user's dotfiles
dotfiles:
  git.latest:
    - name: git@github.com:{{ pillar['github_username'] }}/dotfiles.git
    - rev: master
    - target: /home/{{ pillar['login_user'] }}/dotfiles
    - user: {{ pillar['login_user'] }}
    - require:
      - pkg: git
      - file: github.pky
  cmd.wait:
    - name: git submodule update --init
    - cwd: /home/{{ pillar['login_user'] }}/dotfiles
    - user: {{ pillar['login_user'] }}
    - watch:
      - git: dotfiles

# patch tmux-powerlinerc to set theme
tmux-powerline-theme:
  file.sed:
    - name: /home/{{ pillar['login_user'] }}/dotfiles/tmux/.tmux-powerlinerc
    - before: "TMUX_POWERLINE_THEME=\"mafro\""
    - after: "TMUX_POWERLINE_THEME=\"{{ pillar['tmux-powerline-theme'] }}\""
    - backup: ""
    - require:
      - cmd: dotfiles

# run dotfiles install script
dev-install-dotfiles:
  cmd.run:
    - name: ./install.sh -f vim zsh tmux git &> /dev/null
    - unless: test -L /home/{{ pillar['login_user'] }}/.vimrc
    - cwd: /home/{{ pillar['login_user'] }}/dotfiles
    - user: {{ pillar['login_user'] }}
    - require:
      - cmd: dotfiles
