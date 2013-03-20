from flask.ext.wtf import Form, TextField, PasswordField, validators

from ..models.user import User


class LoginForm(Form):
    username = TextField('username', [validators.Required()])
    password = PasswordField('password', [validators.Required()])

    def validate(self):
        if not super(LoginForm, self).validate():
            return False

        user = User.authenticate(
            username=self.username.data,
            password=self.password.data
        )
        if not user:
            self.username.errors.append('Invalid details.')
            return False

        self.user = user
        return True


class ChangePasswordForm(LoginForm):
    username = TextField('Username', [validators.Required()])
    password = PasswordField('Old Password', [validators.Required()])
    new_password = PasswordField('New Password', [validators.Length(6)])
    confirm_password = PasswordField('Confirm Password', [validators.EqualTo('new_password')])
