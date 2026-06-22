from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, BooleanField, SubmitField, TextAreaField, SelectField, IntegerField, DecimalField, DateField
from wtforms.validators import DataRequired, Email, EqualTo, Length, Optional, NumberRange
from flask_wtf.file import FileField, FileAllowed
import datetime

ALLOWED_FILE_EXTENSIONS = ['jpg', 'jpeg', 'png', 'pdf', 'psd', 'ai']

class RegisterForm(FlaskForm):
    full_name = StringField('Full Name', validators=[DataRequired(), Length(min=2, max=120)])
    company_name = StringField('Company Name', validators=[DataRequired(), Length(min=2, max=150)])
    email = StringField('Email', validators=[DataRequired(), Email(), Length(max=120)])
    password = PasswordField('Password', validators=[DataRequired(), Length(min=8)])
    confirm_password = PasswordField('Confirm Password', validators=[DataRequired(), EqualTo('password')])
    phone = StringField('Phone Number', validators=[Optional(), Length(max=20)])
    whatsapp = StringField('WhatsApp Number', validators=[Optional(), Length(max=20)])
    submit = SubmitField('Create Account')

class LoginForm(FlaskForm):
    email = StringField('Email', validators=[DataRequired(), Email(), Length(max=120)])
    password = PasswordField('Password', validators=[DataRequired()])
    remember = BooleanField('Remember Me')
    submit = SubmitField('Sign In')

class ContactForm(FlaskForm):
    name = StringField('Name', validators=[DataRequired(), Length(min=2, max=120)])
    email = StringField('Email', validators=[DataRequired(), Email(), Length(max=120)])
    phone = StringField('Phone', validators=[Optional(), Length(max=20)])
    message = TextAreaField('Message', validators=[DataRequired(), Length(min=10, max=1000)])
    submit = SubmitField('Send Message')

class ProductForm(FlaskForm):
    name = StringField('Product Name', validators=[DataRequired(), Length(max=160)])
    category_id = SelectField('Category', coerce=int, validators=[DataRequired()])
    description = TextAreaField('Description', validators=[Optional(), Length(max=2000)])
    price = DecimalField('Price', validators=[DataRequired(), NumberRange(min=0)])
    stock = IntegerField('Stock', validators=[DataRequired(), NumberRange(min=0)])
    images = FileField('Product Images', validators=[FileAllowed(ALLOWED_FILE_EXTENSIONS, 'Images only!')])
    is_active = BooleanField('Active', default=True)
    submit = SubmitField('Save Product')

class OrderForm(FlaskForm):
    customer_name = StringField('Customer Name', validators=[DataRequired(), Length(max=120)])
    customer_email = StringField('Customer Email', validators=[DataRequired(), Email(), Length(max=120)])
    customer_phone = StringField('Phone Number', validators=[DataRequired(), Length(max=20)])
    quantity = IntegerField('Quantity', validators=[DataRequired(), NumberRange(min=1)], default=1)
    size = StringField('Size', validators=[Optional(), Length(max=80)])
    material = StringField('Material', validators=[Optional(), Length(max=80)])
    color = StringField('Color Preference', validators=[Optional(), Length(max=80)])
    description = TextAreaField('Detailed Description', validators=[Optional(), Length(max=1500)])
    instructions = TextAreaField('Printing Instructions', validators=[Optional(), Length(max=1500)])
    design_files = FileField('Upload Design Files', validators=[FileAllowed(ALLOWED_FILE_EXTENSIONS, 'Allowed files: JPG, PNG, PDF, PSD, AI')])
    submit = SubmitField('Submit Order')

class CategoryForm(FlaskForm):
    name = StringField('Category Name', validators=[DataRequired(), Length(max=80)])
    submit = SubmitField('Save Category')

class ProfileForm(FlaskForm):
    full_name = StringField('Full Name', validators=[DataRequired(), Length(min=2, max=120)])
    phone = StringField('Phone Number', validators=[Optional(), Length(max=20)])
    whatsapp = StringField('WhatsApp Number', validators=[Optional(), Length(max=20)])
    submit = SubmitField('Update Profile')

class StaffForm(FlaskForm):
    name = StringField('Full Name', validators=[DataRequired(), Length(max=120)])
    position = StringField('Position', validators=[DataRequired(), Length(max=100)])
    department = StringField('Department', validators=[DataRequired(), Length(max=100)])
    email = StringField('Email Address', validators=[DataRequired(), Email(), Length(max=120)])
    phone = StringField('Phone Number', validators=[Optional(), Length(max=20)])
    bio = TextAreaField('Biography/Bio', validators=[DataRequired(), Length(max=1000)])
    joining_date = DateField('Joining Date', default=datetime.date.today, validators=[DataRequired()])
    profile_photo = FileField('Profile Photo', validators=[FileAllowed(['jpg', 'jpeg', 'png'], 'Images only!')])
    submit = SubmitField('Save Staff Member')

class FeedbackForm(FlaskForm):
    rating = SelectField('Rating', choices=[('5', 'Excellent'), ('4', 'Good'), ('3', 'Average'), ('2', 'Poor'), ('1', 'Very Bad')], validators=[DataRequired()])
    comments = TextAreaField('Your Feedback', validators=[DataRequired(), Length(min=5, max=1000)])
    submit = SubmitField('Submit Feedback')
