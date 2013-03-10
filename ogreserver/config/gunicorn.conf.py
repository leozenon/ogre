#import multiprocessing

bind = '127.0.0.1:8005'
#workers = multiprocessing.cpu_count() * 2 + 1
worker_class = 'socketio.sgunicorn.GeventSocketIOWorker'
backlog = 2048
worker_class = "gevent"
debug = True
#daemon = True
proc_name = 'ogre.oii.me.uk'
pidfile = '/tmp/gunicorn-ogre.pid'
#logfile = '/var/log/gunicorn/debug.log'
#loglevel = 'debug'

