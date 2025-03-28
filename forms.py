from flask_wtf import FlaskForm
from wtforms import FileField
from wtforms.validators import DataRequired

class MethodForm(FlaskForm):
    file = FileField(validators=[DataRequired()])
    class Meta:
        csrf = False

class ReportForm(FlaskForm):
    file = FileField(validators=[DataRequired()])
    class Meta:
        csrf = False
