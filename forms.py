from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, SubmitField, SelectField, TextAreaField, FloatField
from wtforms.validators import DataRequired, Email, EqualTo, Optional
from utils.part_code_generator import get_manufacturer_options, get_quality_level_options

class RegistrationForm(FlaskForm):
    email = StringField('Email', validators=[DataRequired(), Email()])
    password = PasswordField('Password', validators=[DataRequired()])
    confirm_password = PasswordField('Confirm Password', validators=[DataRequired(), EqualTo('password')])
    submit = SubmitField('Register')

class PartForm(FlaskForm):
    manufacturer = SelectField('Manufacturer', validators=[DataRequired()])
    quality_level = SelectField('Quality Level', validators=[DataRequired()])
    part_number = StringField('Part Number', validators=[DataRequired()])
    name = StringField('Name', validators=[DataRequired()])
    description = TextAreaField('Description')
    cost_price_dirham = FloatField('Cost Price Dirham', validators=[Optional()])
    cost_price = FloatField('Cost Price', validators=[Optional()])
    selling_price = FloatField('Selling Price', validators=[Optional()])
    location = StringField('Location')
    submit = SubmitField('Add Part')

    def __init__(self, *args, **kwargs):
        super(PartForm, self).__init__(*args, **kwargs)
        self.manufacturer.choices = get_manufacturer_options()
        self.quality_level.choices = get_quality_level_options()