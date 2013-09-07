{% if grains['saltversion'].startswith("0.16") %}

# 2013-08-07 HACK to include pip --pre flag
/usr/lib/pymodules/python2.7/salt/states/pip.py:
  file.managed:
    - source: salt://salt-hack/pip.state.0-16-2.py

/usr/lib/pymodules/python2.7/salt/modules/pip.py:
  file.managed:
    - source: salt://salt-hack/pip.module.0-16-2.py
    - require:
      - file: /usr/lib/pymodules/python2.7/salt/states/pip.py

# 2013-08-08 HACK to fix pre_releases in virtualenv_mod
/usr/lib/pymodules/python2.7/salt/states/virtualenv_mod.py:
  file.managed:
    - source: salt://salt-hack/virtualenv_mod.state.0-16-2.py


# 2013-09-07 apply process group patches for supervisor
/usr/lib/pymodules/python2.7/salt/states/supervisord.py:
  file.managed:
    - source: salt://salt-hack/supervisord.state.py

/usr/lib/pymodules/python2.7/salt/modules/supervisord.py:
  file.managed:
    - source: salt://salt-hack/supervisord.module.py
    - require:
      - file: /usr/lib/pymodules/python2.7/salt/states/supervisord.py


# 2013-09-07 include git.latest unless/onlyif patches
/usr/lib/pymodules/python2.7/salt/states/git.py:
  file.managed:
    - source: salt://salt-hack/git.state.py


salt-hack-restart:
  cmd.run:
    - name: service salt-minion restart
    - watch:
      - file: /usr/lib/pymodules/python2.7/salt/modules/pip.py
      - file: /usr/lib/pymodules/python2.7/salt/states/virtualenv_mod.py
      - file: /usr/lib/pymodules/python2.7/salt/modules/supervisord.py
      - file: /usr/lib/pymodules/python2.7/salt/states/git.py
    - order: 1

{% endif %}
