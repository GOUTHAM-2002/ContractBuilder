from flask_wtf import FlaskForm
from wtforms import StringField, TextAreaField, DecimalField, DateField
from wtforms.validators import DataRequired, Email

class ContractForm(FlaskForm):
    client_name = StringField('Client Name', validators=[DataRequired()])
    client_email = StringField('Client Email', validators=[DataRequired(), Email()])
    agent_email = StringField('Agent Email', validators=[DataRequired(), Email()])
    project_scope = TextAreaField('Project Scope', validators=[DataRequired()])
    total_amount = DecimalField('Total Amount', validators=[DataRequired()])
    start_date = DateField('Start Date', validators=[DataRequired()])
    end_date = DateField('End Date', validators=[DataRequired()])