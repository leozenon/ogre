include:
  - gitrepo
  - ssh
  {% if 'tmux' in pillar.get('extras', []) %}
  - tmux
  {% endif %}

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

# run dotfiles install scripts
{% if 'vim' in pillar.get('extras', []) %}
dotfiles-install-vim:
  cmd.run:
    - name: ./install.sh -f vim &> /dev/null
    - unless: test -L /home/{{ pillar['login_user'] }}/.vimrc
    - cwd: /home/{{ pillar['login_user'] }}/dotfiles
    - user: {{ pillar['login_user'] }}
    - require:
      - cmd: dotfiles
{% endif %}

{% if 'zsh' in pillar.get('extras', []) %}
dotfiles-install-zsh:
  cmd.run:
    - name: ./install.sh -f zsh &> /dev/null
    - unless: test -L /home/{{ pillar['login_user'] }}/.zshrc
    - cwd: /home/{{ pillar['login_user'] }}/dotfiles
    - user: {{ pillar['login_user'] }}
    - require:
      - cmd: dotfiles
{% endif %}

{% if 'git' in pillar.get('extras', []) %}
dotfiles-install-git:
  cmd.run:
    - name: ./install.sh -f git &> /dev/null
    - unless: test -L /home/{{ pillar['login_user'] }}/.gitconfig
    - cwd: /home/{{ pillar['login_user'] }}/dotfiles
    - user: {{ pillar['login_user'] }}
    - require:
      - cmd: dotfiles
{% endif %}
