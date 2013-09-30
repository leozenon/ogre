include:
  - apt
  - vmware-guest-tools
  {% if grains['env'] != 'dev' %}
  - vim
  {% endif %}

git:
  pkg:
    - latest

required-packages:
  pkg.latest:
    - names:
      - ntp
      - debconf-utils
      - swig
      - python-psutil
      - python-pip
    - require:
      - file: apt-no-recommends

esky:
  pip.installed:
    - require:
      - pkg: required-packages

pip-pip:
  pip.installed:
    - name: pip
    - upgrade: true
    - require:
      - pkg: required-packages

pip-distribute:
  pip.installed:
    - name: distribute
    - upgrade: true
    - require:
      - pkg: required-packages

{% if pillar.get('timezone', false) %}
{{ pillar['timezone'] }}:
  timezone.system:
    - utc: True
{% endif %}
