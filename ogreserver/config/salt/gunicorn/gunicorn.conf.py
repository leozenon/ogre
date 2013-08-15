#################################################
# Gunicorn config for ogreserver
#
# This is loaded via Supervisor into Gunicorn
# 
#################################################

import multiprocessing

bind = '127.0.0.1:{{ gunicorn_port }}'
workers = multiprocessing.cpu_count() * 2 + 1
worker_class = 'socketio.sgunicorn.GeventSocketIOWorker'
backlog = 2048
worker_class = "gevent"
debug = True
proc_name = 'gunicorn-{{ app_name }}.pid'
pidfile = '/tmp/gunicorn-{{ app_name }}.pid'
logfile = '/var/log/{{ app_name }}/gunicorn.log'
loglevel = 'info'
