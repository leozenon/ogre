{% if grains['osrelease'].startswith("13") or grains['os'] == "Debian" %}
  {% set install_path = "/usr/lib/python2.7/dist-packages" %}
{% else %}
  {% set install_path = "/usr/lib/pymodules/python2.7" %}
{% endif %}

{% if grains['saltversion'].startswith("0.16") %}

# 2013-08-07 HACK to include pip --pre flag
{{ install_path }}/salt/states/pip.py:
  file.managed:
    - source: salt://salt-hack/pip.state.0-16-2.py

{{ install_path }}/salt/modules/pip.py:
  file.managed:
    - source: salt://salt-hack/pip.module.0-16-2.py
    - require:
      - file: {{ install_path }}/salt/states/pip.py

# 2013-08-08 HACK to fix pre_releases in virtualenv_mod
{{ install_path }}/salt/states/virtualenv_mod.py:
  file.managed:
    - source: salt://salt-hack/virtualenv_mod.state.0-16-2.py


# 2013-09-07 apply process group patches for supervisor
{{ install_path }}/salt/states/supervisord.py:
  file.managed:
    - source: salt://salt-hack/supervisord.state.py

{{ install_path }}/salt/modules/supervisord.py:
  file.managed:
    - source: salt://salt-hack/supervisord.module.py
    - require:
      - file: {{ install_path }}/salt/states/supervisord.py


# 2013-09-07 include git.latest unless/onlyif patches
{{ install_path }}/salt/states/git.py:
  file.managed:
    - source: salt://salt-hack/git.state.py


salt-hack-restart:
  cmd.run:
    - name: service salt-minion restart
    - watch:
      - file: {{ install_path }}/salt/modules/pip.py
      - file: {{ install_path }}/salt/states/virtualenv_mod.py
      - file: {{ install_path }}/salt/modules/supervisord.py
      - file: {{ install_path }}/salt/states/git.py
    - order: 1

{% endif %}
