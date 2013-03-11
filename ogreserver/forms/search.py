from flask.ext.wtf import Form, TextField, validators


class SearchForm(Form):
    searchtext = TextField('searchtext', [validators.Required()])
