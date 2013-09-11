include:
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
      - htop
      - stow

# install some extra packages
{% for package_name in pillar.get('extras', []) %}
extra_{{ package_name }}:
  pkg.installed:
    - name: {{ package_name }}
{% endfor %}

# set the default shell
shell-{{ pillar['shell'] }}:
  pkg.installed:
    - name: {{ pillar['shell'] }}

modify-login-user:
  user.present:
    - name: {{ pillar['login_user'] }}
    - shell: /bin/{{ pillar['shell'] }}
    - unless: getent passwd $LOGNAME | grep {{ pillar['shell'] }}
    - require:
      - pkg: shell-{{ pillar['shell'] }}

# grab the user's dotfiles
dotfiles:
  git.latest:
    - name: git@github.com:{{ pillar['github_username'] }}/dotfiles.git
    - target: /home/{{ pillar['login_user'] }}/dotfiles
    - user: {{ pillar['login_user'] }}
    - submodules: true
    - require:
      - pkg: git
      {% if pillar.get('github_key_path', False) %}
      - file: github.pky
      {% endif %}

# run dotfiles install scripts
{% if 'vim' in pillar.get('extras', []) %}
dotfiles-install-vim:
  cmd.run:
    - name: ./install.sh -f vim &> /dev/null
    - unless: test -L /home/{{ pillar['login_user'] }}/.vimrc
    - cwd: /home/{{ pillar['login_user'] }}/dotfiles
    - user: {{ pillar['login_user'] }}
    - require:
      - git: dotfiles
      - pkg: dev_packages

# prevent ~/.viminfo being owned by root
viminfo-touch:
  file.managed:
    - name: /home/{{ pillar['login_user'] }}/.viminfo
    - user: {{ pillar['login_user'] }}
    - group: {{ pillar['login_user'] }}
    - mode: 644
{% endif %}

{% if 'zsh' in pillar.get('extras', []) %}
dotfiles-install-zsh:
  cmd.run:
    - name: ./install.sh -f zsh &> /dev/null
    - unless: test -L /home/{{ pillar['login_user'] }}/.zshrc
    - cwd: /home/{{ pillar['login_user'] }}/dotfiles
    - user: {{ pillar['login_user'] }}
    - require:
      - git: dotfiles
      - pkg: dev_packages
{% endif %}

{% if 'git' in pillar.get('extras', []) %}
dotfiles-install-git:
  cmd.run:
    - name: ./install.sh -f git &> /dev/null
    - unless: test -L /home/{{ pillar['login_user'] }}/.gitconfig
    - cwd: /home/{{ pillar['login_user'] }}/dotfiles
    - user: {{ pillar['login_user'] }}
    - require:
      {% if 'vim' in pillar.get('extras', []) %}
      - file: viminfo-touch
      {% endif %}
      - git: dotfiles
      - pkg: dev_packages
{% endif %}
