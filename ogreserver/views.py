import base64
import json

from flask import request, redirect, session, url_for, render_template, jsonify
from flask.ext.login import login_required, login_user, logout_user, current_user

from werkzeug.exceptions import Forbidden

from ogreserver import app, uploads

from ogreserver.forms.auth import LoginForm

from ogreserver.models.user import User
from ogreserver.models.datastore import DataStore
from ogreserver.models.reputation import Reputation
from ogreserver.models.log import Log

from ogreserver.tasks import store_ebook


@app.route("/")
@login_required
def index():
    return redirect(url_for("home"))


@app.route("/login", methods=['GET', 'POST'])
def login():
    form = LoginForm()
    if form.validate_on_submit():
        login_user(form.user)
        session['user_id'] = form.user.id
        return redirect(request.args.get("next") or url_for("index"))
    return render_template("login.html", form=form)


@app.route("/auth", methods=['POST'])
def auth():
    user = User.authenticate(
        username=request.form.get("username"),
        password=request.form.get("password")
    )
    if user == None:
        raise Forbidden
    else:
        return base64.b64encode(user.assign_auth_key())


@app.route("/logout")
@login_required
def logout():
    logout_user()
    return redirect(url_for('login'))


@app.route("/home")
@login_required
def home():
    return dedrm()


@app.route("/list", methods=['GET', 'POST'])
@login_required
def list():
    ds = DataStore(current_user)
    s = request.args.get("s")
    if s is None:
        rs = ds.list()
    else:
        rs = ds.search(s)
    return render_template("list.html", ebooks=rs)


@app.route("/ajax/rating/<sdb_key>")
@login_required
def get_rating(sdb_key):
    rating = DataStore.get_rating(sdb_key)
    return jsonify({'rating': rating})


@app.route("/ajax/comment-count/<sdb_key>")
@login_required
def get_comment_count(sdb_key):
    comments = DataStore.get_comments(sdb_key)
    return jsonify({'comments': len(comments)})


@app.route("/view")
@login_required
def view(sdbkey=None):
    ds = DataStore(current_user)
    rs = ds.list()
    return render_template("view.html", ebooks=rs)


@app.route('/download/<sdb_key>/', defaults={'fmt': None})
@app.route("/download/<sdb_key>/<fmt>")
@login_required
def download(sdb_key, fmt=None):
    return redirect(DataStore.get_ebook_url(sdb_key, fmt))


@app.route("/dedrm")
@login_required
def dedrm():
    return render_template("dedrm.html")


@app.route("/post/<auth_key>", methods=['POST'])
def post(auth_key):
    # authenticate user
    key_parts = base64.b64decode(str(auth_key), "_-").split("+")
    user = User.validate_auth_key(
        username=key_parts[0],
        api_key=key_parts[1]
    )
    if user is None:
        raise Forbidden

    # get the json payload
    data = json.loads(request.form.get("ebooks"))

    # stats log the upload
    Log.create(user.id, "CONNECT", request.form.get("total"), key_parts[1])

    # update the library
    ds = DataStore(user)
    new_ebook_count = ds.update_library(data)
    Log.create(user.id, "NEW", new_ebook_count, key_parts[1])

    # handle badge and reputation changes
    r = Reputation(user)
    r.new_ebooks(new_ebook_count)
    r.earn_badges()
    msgs = r.get_new_badges()

    # query books missing from S3 and supply back to the client
    rs = DataStore.get_missing_books(username=user.username)
    return json.dumps({
        'ebooks_to_upload': rs,
        'messages': msgs
    })


@app.route("/upload/<auth_key>", methods=['POST'])
def upload(auth_key):
    key_parts = base64.b64decode(str(auth_key), "_-").split("+")
    user = User.validate_auth_key(
        username=key_parts[0],
        api_key=key_parts[1]
    )
    if user is None:
        return "OGRESERVER Auth Failed in upload()"

    # stats log the upload
    Log.create(user.id, "UPLOADED", 1, key_parts[1])

    print key_parts[1], request.form.get("sdb_key"), request.files['ebook'].content_length

    # write uploaded ebook to disk, named as the hash and filetype
    uploads.save(request.files['ebook'], None, "%s.%s" % (request.form.get("filemd5"), request.form.get("format")))

    # let celery process the upload
    res = store_ebook.delay(user.id,
                            request.form.get("sdb_key"),
                            request.form.get("authortitle"),
                            request.form.get("filemd5"),
                            request.form.get("version"),
                            request.form.get("format"))
    return res.task_id


@app.route("/result/<int:task_id>")
def show_result(task_id):
    retval = store_ebook.AsyncResult(task_id).get(timeout=1.0)
    return repr(retval)
