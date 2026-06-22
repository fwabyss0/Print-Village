# Email Configuration Setup Guide

## Gmail App Password Setup

To enable email functionality for Print Village, you need to set up a Gmail App Password:

### Step 1: Enable 2-Factor Authentication
1. Go to https://myaccount.google.com/security
2. Enable 2-Step Verification if not already enabled

### Step 2: Generate App Password
1. Go to https://myaccount.google.com/apppasswords
2. Select "Mail" from the app dropdown
3. Select "Other (Custom name)" and enter "Print Village"
4. Click "Generate"
5. Copy the 16-character password (without spaces)

### Step 3: Configure Environment Variable

Set the `MAIL_PASSWORD` environment variable to your app password:

**Windows (Command Prompt):**
```cmd
set MAIL_PASSWORD=your_app_password_here
```

**Windows (PowerShell):**
```powershell
$env:MAIL_PASSWORD="your_app_password_here"
```

**Linux/Mac:**
```bash
export MAIL_PASSWORD=your_app_password_here
```

**Or add to your .env file:**
```
MAIL_PASSWORD=your_app_password_here
```

### Step 4: Restart Application

Restart your Flask application for the changes to take effect.

## Testing Email Functionality

After configuration, email will be automatically sent for:
- New order alerts to admin (print.resolution@gmail.com)
- Order claimed notifications to customers
- Order completed notifications to customers
- Order denied notifications to customers

## Troubleshooting

If emails are not sending:
1. Verify the app password is correct
2. Check that 2-factor authentication is enabled
3. Ensure the email address (print.resolution@gmail.com) is accessible
4. Check application logs for SMTP errors
