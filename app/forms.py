from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, SelectField, SubmitField
from wtforms.validators import DataRequired, Email, Length, EqualTo, ValidationError, Optional
from app.models.user import User
from app.church_data import get_archdeaconries, get_parishes, CHURCH_DATA


class LoginForm(FlaskForm):
    email = StringField('Email', validators=[DataRequired(), Email()])
    password = PasswordField('Password', validators=[DataRequired()])
    submit = SubmitField('Login')


class RegistrationForm(FlaskForm):
    name = StringField('Full Name', validators=[DataRequired(), Length(min=2, max=100)])
    email = StringField('Email', validators=[DataRequired(), Email()])
    phone = StringField('Phone Number', validators=[Optional(), Length(min=10, max=15)])
    role = SelectField('Role', choices=[
        ('chair', 'Chair'),
        ('youth_minister', 'Youth Minister'),
    ], validators=[DataRequired()])
    local_church = StringField('Local Church', validators=[DataRequired(), Length(max=100)])
    archdeaconry = SelectField('Archdeaconry', validators=[DataRequired()])
    parish = SelectField('Parish', validators=[DataRequired()])
    password = PasswordField('Password', validators=[DataRequired(), Length(min=6)])
    confirm_password = PasswordField('Confirm Password', validators=[
        DataRequired(), 
        EqualTo('password', message='Passwords must match')
    ])
    submit = SubmitField('Register')
    
    def __init__(self, *args, **kwargs):
        super(RegistrationForm, self).__init__(*args, **kwargs)
        self.archdeaconry.choices = get_archdeaconries()
        self.parish.choices = get_parishes()
    
    def validate_email(self, email):
        user = User.query.filter_by(email=email.data).first()
        if user:
            raise ValidationError('Email already registered. Please use a different email.')
    
    def validate_phone(self, phone):
        if phone.data:
            user = User.query.filter_by(phone=phone.data).first()
            if user:
                raise ValidationError('Phone number already registered.')


class DelegateForm(FlaskForm):
    name = StringField('Full Name', validators=[DataRequired(), Length(min=2, max=100)])
    local_church = StringField('Local Church', validators=[DataRequired(), Length(max=100)])
    archdeaconry = SelectField('Archdeaconry', validators=[DataRequired()])
    parish = SelectField('Parish', validators=[DataRequired()])
    phone_number = StringField('Phone Number (Optional)', validators=[Optional(), Length(max=15)])
    gender = SelectField('Gender', choices=[
        ('male', 'Male'),
        ('female', 'Female')
    ], validators=[DataRequired()])
    submit = SubmitField('Register Delegate')
    
    def __init__(self, *args, **kwargs):
        super(DelegateForm, self).__init__(*args, **kwargs)
        self.archdeaconry.choices = get_archdeaconries()
        self.parish.choices = get_parishes()


class PaymentForm(FlaskForm):
    phone_number = StringField('M-Pesa Phone Number', validators=[
        DataRequired(), 
        Length(min=10, max=15)
    ])
    submit = SubmitField('Pay Now')


class AdminUserForm(FlaskForm):
    """Form for admin to create/edit users"""
    name = StringField('Full Name', validators=[DataRequired(), Length(min=2, max=100)])
    email = StringField('Email', validators=[DataRequired(), Email()])
    phone = StringField('Phone Number', validators=[Optional(), Length(min=10, max=15)])
    role = SelectField('Role', choices=[
        ('chair', 'Chair'),
        ('youth_minister', 'Youth Minister'),
        ('admin', 'Admin'),
    ], validators=[DataRequired()])
    local_church = StringField('Local Church', validators=[Optional(), Length(max=100)])
    archdeaconry = SelectField('Archdeaconry', validators=[Optional()])
    parish = SelectField('Parish', validators=[Optional()])
    password = PasswordField('Password (leave blank to keep current)', validators=[Optional(), Length(min=6)])
    submit = SubmitField('Save User')
    
    def __init__(self, *args, **kwargs):
        super(AdminUserForm, self).__init__(*args, **kwargs)
        self.archdeaconry.choices = get_archdeaconries()
        self.parish.choices = get_parishes()
