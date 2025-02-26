from flask_wtf import FlaskForm
from wtforms import StringField, TextAreaField, FloatField, DateField, EmailField
from wtforms.validators import DataRequired, Email

class ContractForm(FlaskForm):
    client_name = StringField('Client Name', validators=[DataRequired()])
    client_email = EmailField('Client Email', validators=[DataRequired(), Email()])
    agent_email = EmailField('Agent Email', validators=[DataRequired(), Email()])
    project_scope = TextAreaField('Project Scope', validators=[DataRequired()])
    total_amount = FloatField('Total Amount', validators=[DataRequired()])
    start_date = DateField('Start Date', validators=[DataRequired()])
    end_date = DateField('End Date', validators=[DataRequired()])