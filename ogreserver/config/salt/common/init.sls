include:
  - apt
  - vmware-guest-tools
  {% if grains['env'] != 'dev' %}
  - vim
  {% endif %}

{% if grains['oscodename'] == "wheezy" %}
wheezy-backports-pkgrepo:
  pkgrepo.managed:
    - humanname: Wheezy Backports
    - name: deb http://{{ pillar.get('deb_mirror_prefix', 'ftp.us') }}.debian.org/debian wheezy-backports main
    - file: /etc/apt/sources.list.d/wheezy-backports.list
    - require_in:
      - pkg: git
{% endif %}

git:
  pkg:
    - latest
    {% if grains['oscodename'] == "wheezy" %}
    - fromrepo: wheezy-backports
    {% endif %}

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
