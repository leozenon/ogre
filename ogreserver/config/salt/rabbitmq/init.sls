/etc/hostname:
  file.managed:
    - contents: {{ pillar['app_name'] }}

/etc/hosts:
  file.append:
    - text: 127.0.0.1 {{ pillar['app_name'] }}

set-hostname:
  cmd.run:
    - name: hostname -F /etc/hostname
    - require:
      - file: /etc/hostname
      - file: /etc/hosts

rabbitmq-pkgrepo:
  pkgrepo.managed:
    - humanname: RabbitMQ PPA
    - name: deb http://www.rabbitmq.com/debian testing main
    - file: /etc/apt/sources.list.d/rabbitmq.list
    - key_url: http://www.rabbitmq.com/rabbitmq-signing-key-public.asc
    - require_in:
      - pkg: rabbitmq-server

rabbitmq-server:
  pkg:
    - installed
  service.running:
    - enable: true
    - require:
      - pkg: rabbitmq-server

rabbitmq-server-running:
  cmd.run:
    - name: rabbitmq-server -detached
    - onlyif: rabbitmqctl status 2>&1 | grep nodedown
    - require:
      - pkg: rabbitmq-server

rabbitmq-guest-remove:
  rabbitmq_user.absent:
    - require:
      - cmd: rabbitmq-server-running

rabbitmq-user:
  rabbitmq_user.present:
    - name: {{ pillar['rabbitmq_user'] }}
    - password: {{ pillar['rabbitmq_pass'] }}
    - require:
      - cmd: rabbitmq-server-running

rabbitmq-vhost:
  rabbitmq_vhost.present:
    - name: {{ pillar['rabbitmq_vhost'] }}
    - user: {{ pillar['rabbitmq_user'] }}
    - require:
      - rabbitmq_user: rabbitmq-user
