import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from flask import current_app

def wrap_email_layout(title, body_content):
    """Wraps body content in a premium responsive HTML email layout"""
    return f"""
    <!DOCTYPE html>
    <html>
    <head>
      <meta charset="utf-8">
      <style>
        body {{
          font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
          margin: 0;
          padding: 0;
          background-color: #f4f5f7;
          color: #333333;
        }}
        .container {{
          max-width: 600px;
          margin: 40px auto;
          background: #ffffff;
          border-radius: 14px;
          border: 1px solid #e1e4e8;
          overflow: hidden;
          box-shadow: 0 4px 15px rgba(0,0,0,0.05);
        }}
        .header {{
          background: linear-gradient(135deg, #6C63FF, #FF6584);
          padding: 30px;
          text-align: center;
        }}
        .header h1 {{
          margin: 0;
          font-size: 24px;
          color: #ffffff;
          font-weight: 800;
          letter-spacing: 1px;
        }}
        .content {{
          padding: 40px 30px;
          line-height: 1.6;
          color: #444444;
        }}
        .content h2, .content h3 {{
          color: #111111;
          margin-top: 0;
        }}
        .footer {{
          background-color: #f8f9fa;
          padding: 20px;
          text-align: center;
          font-size: 12px;
          color: #6c757d;
          border-top: 1px solid #e1e4e8;
        }}
        .btn {{
          display: inline-block;
          padding: 12px 24px;
          background-color: #6C63FF;
          color: #ffffff !important;
          text-decoration: none;
          border-radius: 8px;
          font-weight: bold;
          margin-top: 20px;
        }}
      </style>
    </head>
    <body>
      <div class="container">
        <div class="header">
          <h1>{title}</h1>
        </div>
        <div class="content">
          {body_content}
        </div>
        <div class="footer">
          <p>© 2026 Print Village. All rights reserved.</p>
          <p>Kathmandu, Nepal | +977 98-0000-0000 | print.resolution01@gmail.com</p>
        </div>
      </div>
    </body>
    </html>
    """

from flask_mail import Message
from app.extensions import mail

def send_mail(to_email, subject, body_content):
    """
    Production-ready robust SMTP email dispatcher using Flask-Mail
    """
    try:
        sender_addr = current_app.config.get('MAIL_DEFAULT_SENDER', 'print.resolution@gmail.com')
        
        # Wrap the body in our email layout
        html_content = wrap_email_layout(subject, body_content)
        
        msg = Message(subject=subject, recipients=[to_email], sender=sender_addr)
        msg.html = html_content
        
        mail.send(msg)
        
        # Log email to DB for visibility matching audit trail requirements
        from app.extensions import db
        from app.models import EmailLog
        try:
            log_entry = EmailLog(recipient=to_email, subject=subject, body=html_content[:4000])
            db.session.add(log_entry)
            db.session.commit()
        except Exception as e:
            print(f"Failed to log email: {e}")
            db.session.rollback()
            
        return True
    except Exception as ex:
        print(f"Flask-Mail Dispatch Failure: {ex}")
        # Graceful fallback to avoid halting application operations if SMTP server connection times out
        return False

def get_feedback_link(order_id):
    """Generates the absolute feedback acquisition link for completed orders"""
    from flask import url_for
    try:
        return url_for('buyer.feedback_submission', oid=order_id, _external=True)
    except RuntimeError:
        return f"http://localhost:5000/buyer/orders/{order_id}/feedback"