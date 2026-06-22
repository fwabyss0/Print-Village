import random
from datetime import datetime, timedelta
from flask import Blueprint, render_template, redirect, url_for, flash, request, current_app, jsonify
from flask_login import login_user, logout_user, login_required
from app.extensions import db
from app.models import User, Role
from app.utils.email import send_mail

bp = Blueprint('auth', __name__, url_prefix='/auth')


def generate_and_send_otp(user):
    """Generates a 6-digit OTP code, saves it to the user record, and attempts to email it."""
    otp = f"{random.randint(100000, 999999)}"
    user.otp_code = otp
    user.otp_expiry = datetime.utcnow() + timedelta(minutes=15)
    db.session.commit()
    
    subject = "Verify Your Print Village Account - Verification Code"
    body = f"""
    <h2>Verify Your Email Address</h2>
    <p>Dear {user.full_name},</p>
    <p>Thank you for registering a Customer account with Print Village for <strong>{user.company_name}</strong>.</p>
    <p>Your 6-digit verification code is:</p>
    <div style="font-size: 28px; font-weight: bold; color: #6C63FF; padding: 10px 20px; background: #f4f5f7; display: inline-block; border-radius: 8px; letter-spacing: 4px; margin: 15px 0;">
      {otp}
    </div>
    <p>This code will expire in 15 minutes.</p>
    <p>Please enter this code on the verification page to activate your account.</p>
    <p>Best regards,<br/>The Print Village Team</p>
    """
    
    success = send_mail(user.email, subject, body)
    return success


@bp.route('/register', methods=['GET','POST'])
def register():
    if request.method == 'POST':
        f = request.form
        if not f.get('company_name'):
            flash('Company name is required', 'danger')
            return redirect(url_for('auth.register'))
        if f['password'] != f['confirm_password']:
            flash('Passwords do not match','danger')
            return redirect(url_for('auth.register'))
        if User.query.filter_by(email=f['email']).first():
            flash('Email already registered','danger')
            return redirect(url_for('auth.register'))
        role = Role.query.filter_by(name='customer').first()
        if not role:
            role = Role(name='customer')
            db.session.add(role)
            db.session.flush()
        u = User(
            full_name=f['full_name'],
            email=f['email'],
            phone=f.get('phone'),
            whatsapp=f.get('whatsapp'),
            company_name=f.get('company_name'),
            role_id=role.id,
            is_active_account=True,
            email_verified=False
        )
        u.set_password(f['password'])
        db.session.add(u)
        db.session.commit()
        
        mail_configured = current_app.config.get('MAIL_PASSWORD') and current_app.config.get('MAIL_PASSWORD') != 'APP_PASSWORD'
        if generate_and_send_otp(u):
            flash('Registration successful! Please check your email for the verification code.', 'success')
            return redirect(url_for('auth.verify_otp', email=u.email))
        elif not mail_configured:
            # Email send failure: bypass email verification
            u.email_verified = True
            db.session.commit()
            login_user(u)
            flash('Registration successful! Email verification bypassed as mail server is not configured.', 'success')
            return redirect(url_for('buyer.dashboard'))
        else:
            flash('Failed to send verification email. Please check your email configuration.', 'danger')
            return redirect(url_for('auth.register'))
            
    return render_template('auth/register.html')


@bp.route('/verify-otp', methods=['GET', 'POST'])
def verify_otp():
    email = request.args.get('email') or request.form.get('email')
    if not email:
        flash('Invalid verification request.', 'danger')
        return redirect(url_for('auth.login'))
        
    u = User.query.filter_by(email=email).first_or_404()
    if u.email_verified:
        flash('Your email is already verified. Please log in.', 'info')
        return redirect(url_for('auth.login'))
        
    if request.method == 'POST':
        code_entered = request.form.get('otp', '').strip()
        if not u.otp_code or u.otp_code != code_entered:
            flash('Invalid verification code.', 'danger')
            return render_template('auth/verify_otp.html', email=email)
            
        if u.otp_expiry and datetime.utcnow() > u.otp_expiry:
            flash('The verification code has expired. Click below to resend code.', 'danger')
            return render_template('auth/verify_otp.html', email=email)
            
        # Success!
        u.email_verified = True
        u.otp_code = None
        u.otp_expiry = None
        db.session.commit()
        login_user(u)
        flash(f'Welcome to Print Village, {u.full_name}! Your email has been verified.', 'success')
        return redirect(url_for('buyer.dashboard'))
        
    return render_template('auth/verify_otp.html', email=email)


@bp.route('/resend-otp', methods=['POST'])
def resend_otp():
    email = request.form.get('email')
    if not email:
        return jsonify({'success': False, 'message': 'Email is required.'}), 400
        
    u = User.query.filter_by(email=email).first()
    if not u:
        return jsonify({'success': False, 'message': 'User not found.'}), 404
        
    if u.email_verified:
        return jsonify({'success': False, 'message': 'Email is already verified.'}), 400
        
    mail_configured = current_app.config.get('MAIL_PASSWORD') and current_app.config.get('MAIL_PASSWORD') != 'APP_PASSWORD'
    if generate_and_send_otp(u):
        return jsonify({'success': True, 'message': 'A new verification code has been sent to your email.'})
    elif not mail_configured:
        # Bypassed if we can't send
        u.email_verified = True
        u.otp_code = None
        u.otp_expiry = None
        db.session.commit()
        login_user(u)
        return jsonify({
            'success': True, 
            'bypassed': True, 
            'message': 'Email verification bypassed as mail server is not configured. Redirecting...'
        })
    else:
        return jsonify({'success': False, 'message': 'Failed to send verification email. Please check your email configuration.'}), 500


@bp.route('/login', methods=['GET','POST'])
def login():
    if request.method == 'POST':
        u = User.query.filter_by(email=request.form['email']).first()
        if u and u.check_password(request.form['password']) and u.is_active_account:
            if u.role_name != 'admin' and not u.email_verified:
                mail_configured = current_app.config.get('MAIL_PASSWORD') and current_app.config.get('MAIL_PASSWORD') != 'APP_PASSWORD'
                # Try sending a new OTP
                if generate_and_send_otp(u):
                    flash('Please verify your email address. A verification code has been sent.', 'warning')
                    return redirect(url_for('auth.verify_otp', email=u.email))
                elif not mail_configured:
                    # Email send failure: bypass verification
                    u.email_verified = True
                    db.session.commit()
                    login_user(u, remember=bool(request.form.get('remember')))
                    flash(f'Welcome back, {u.full_name} (Email verification bypassed).', 'success')
                    if u.role_name == 'admin':  return redirect(url_for('admin.dashboard'))
                    return redirect(url_for('buyer.dashboard'))
                else:
                    flash('Failed to send verification email. Please verify your email configuration.', 'danger')
                    return redirect(url_for('auth.login'))
            
            login_user(u, remember=bool(request.form.get('remember')))
            flash(f'Welcome back, {u.full_name}','success')
            if u.role_name == 'admin':  return redirect(url_for('admin.dashboard'))
            return redirect(url_for('buyer.dashboard'))
        flash('Invalid credentials','danger')
    return render_template('auth/login.html')


@bp.route('/logout')
@login_required
def logout():
    logout_user()
    flash('Logged out','info')
    return redirect(url_for('main.index'))


@bp.route('/forgot-password', methods=['GET', 'POST'])
def forgot_password():
    if request.method == 'POST':
        email = request.form.get('email', '').strip()
        u = User.query.filter_by(email=email).first()
        if not u:
            flash('If the email is registered, you will receive a reset code shortly.', 'info')
            return redirect(url_for('auth.login'))
        
        otp = f"{random.randint(100000, 999999)}"
        u.otp_code = otp
        u.otp_expiry = datetime.utcnow() + timedelta(minutes=15)
        db.session.commit()
        
        subject = "Reset Your Print Village Password"
        body = f"""
        <h2>Password Reset Request</h2>
        <p>Dear {u.full_name},</p>
        <p>We received a request to reset the password for your account.</p>
        <p>Your password reset code is:</p>
        <div style="font-size: 28px; font-weight: bold; color: #6C63FF; padding: 10px 20px; background: #f4f5f7; display: inline-block; border-radius: 8px; letter-spacing: 4px; margin: 15px 0;">
          {otp}
        </div>
        <p>This code will expire in 15 minutes.</p>
        <p>Please enter this code on the password reset page to update your password.</p>
        <p>Best regards,<br/>The Print Village Team</p>
        """
        
        mail_configured = current_app.config.get('MAIL_PASSWORD') and current_app.config.get('MAIL_PASSWORD') != 'APP_PASSWORD'
        if send_mail(u.email, subject, body):
            flash('A password reset code has been sent to your email.', 'success')
            return redirect(url_for('auth.reset_password', email=u.email))
        elif not mail_configured:
            flash('Email sending bypassed as mail server is not configured. Redirecting to reset page...', 'warning')
            return redirect(url_for('auth.reset_password', email=u.email, bypass_otp=otp))
        else:
            flash('Failed to send reset code. Please check email settings.', 'danger')
            
    return render_template('auth/forgot_password.html')


@bp.route('/reset-password', methods=['GET', 'POST'])
def reset_password():
    email = request.args.get('email') or request.form.get('email')
    bypass_otp = request.args.get('bypass_otp')
    if not email:
        flash('Invalid password reset request.', 'danger')
        return redirect(url_for('auth.login'))
        
    u = User.query.filter_by(email=email).first_or_404()
    
    if request.method == 'POST':
        otp_entered = request.form.get('otp', '').strip()
        new_password = request.form.get('password')
        confirm_password = request.form.get('confirm_password')
        
        if new_password != confirm_password:
            flash('Passwords do not match.', 'danger')
            return render_template('auth/reset_password.html', email=email, bypass_otp=bypass_otp)
            
        mail_configured = current_app.config.get('MAIL_PASSWORD') and current_app.config.get('MAIL_PASSWORD') != 'APP_PASSWORD'
        
        if mail_configured:
            if not u.otp_code or u.otp_code != otp_entered:
                flash('Invalid reset code.', 'danger')
                return render_template('auth/reset_password.html', email=email)
            if u.otp_expiry and datetime.utcnow() > u.otp_expiry:
                flash('The reset code has expired. Please request a new one.', 'danger')
                return redirect(url_for('auth.forgot_password'))
        else:
            if bypass_otp and u.otp_code != bypass_otp:
                flash('Invalid reset session.', 'danger')
                return redirect(url_for('auth.forgot_password'))

        u.set_password(new_password)
        u.otp_code = None
        u.otp_expiry = None
        db.session.commit()
        
        flash('Your password has been reset successfully. Please log in.', 'success')
        return redirect(url_for('auth.login'))
        
    return render_template('auth/reset_password.html', email=email, bypass_otp=bypass_otp)