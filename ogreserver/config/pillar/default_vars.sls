project_name: ogre
app_name: ogreserver
app_user: vagrant
login_user: vagrant

gunicorn_port: 8005

mysql_host: localhost
mysql_db: ogre
mysql_user: ogreserver
mysql_pass: ihatedrm

rabbitmq_host: localhost
rabbitmq_vhost: dev
rabbitmq_user: dev
rabbitmq_pass: dev

flask_secret: eggs_are_really_nice
aws_access_key: ""
aws_secret_key: ""
aws_region: eu-west-1
s3_bucket: ""

ogre_user_name: dev
ogre_user_pass: dev
ogre_user_email: dev@dev.dev

watchdog:
  gunicorn: "*.py"
  celeryd: "*.py"

timezone: "Australia/Melbourne"

deb_mirror_prefix: ftp.uk
github_username: mafrosis
shell: zsh
tmux_patched_font: true             # http://bit.ly/Xw51zu
#yahoo_weather_location: 12707465    # http://bit.ly/12uC3TF
extras:
  - vim
  - zsh
  - tmux
  - pyflakes
