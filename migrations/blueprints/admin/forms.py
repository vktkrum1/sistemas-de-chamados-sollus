from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, SelectField, BooleanField, SubmitField
from wtforms.validators import DataRequired, Email

class UserForm(FlaskForm):
    name = StringField('Nome', validators=[DataRequired()])
    email = StringField('E-mail', validators=[DataRequired(), Email()])
    role = SelectField('Perfil', choices=[('user','Usuário'),('agent','Agente'),('admin','Admin')])
    password = PasswordField('Senha (deixe em branco para manter)')
    is_active = BooleanField('Ativo', default=True)
    submit = SubmitField('Salvar')
