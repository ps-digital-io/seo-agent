import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.application import MIMEApplication
import streamlit as st
import os

class EmailSender:
    def __init__(self):
        """Initialize email configuration from Streamlit secrets"""
        self.smtp_server = st.secrets["email"]["smtp_server"]
        self.smtp_port = st.secrets["email"]["smtp_port"]
        self.sender_email = st.secrets["email"]["sender_email"]
        self.sender_password = st.secrets["email"]["sender_password"]
        self.sender_name = st.secrets["email"]["sender_name"]
    
    def send_onboarding_email(self, recipient_email, recipient_name, website_url, service_account_email):
        """Send onboarding instructions to new users"""
        
        subject = f"Complete Your SEO Audit Setup - {website_url}"
        
        body = f"""
Hi {recipient_name},

Thanks for requesting a comprehensive SEO audit for {website_url}!

To unlock the full audit with Google Search Console and Google Analytics data, please grant us view access to your properties.

📧 EMAIL TO ADD: {service_account_email}

═══════════════════════════════════════

STEP 1: Google Search Console (2 minutes)

1. Go to: https://search.google.com/search-console
2. Select your property for {website_url}
3. Click Settings (gear icon, left sidebar)
4. Click "Users and permissions"
5. Click "Add user"
6. Enter email: {service_account_email}
7. Permission level: "Full" or "Restricted" (either works)
8. Click "Add"

═══════════════════════════════════════

STEP 2: Google Analytics 4 (2 minutes)

1. Go to: https://analytics.google.com
2. Select your GA4 property
3. Click "Admin" (gear icon, bottom left)
4. Under "Property", click "Property access management"
5. Click the "+" icon (top right) → "Add users"
6. Enter email: {service_account_email}
7. Select role: "Viewer"
8. Uncheck "Notify new users by email"
9. Click "Add"

═══════════════════════════════════════

Once you've completed both steps, run the audit again at https://punkaj.streamlit.app/ and you'll get the full report with real data!

Questions? Just reply to this email.

Best regards,
{self.sender_name}
SEO & Digital Marketing Consultant
📧 {self.sender_email}
🌐 psdigital.io
💼 linkedin.com/in/punkaj

P.S. If you don't have access to GSC or GA4, no problem! We can still run a basic technical audit for you.
        """.strip()
        
        return self._send_email(recipient_email, subject, body)
    
    def send_audit_complete_email(self, recipient_email, recipient_name, website_url, pdf_path=None):
        """Send notification when audit is complete with PDF attachment"""
        
        subject = f"Your SEO Audit Report is Ready - {website_url}"
        
        body = f"""
Hi {recipient_name},

Great news! Your comprehensive SEO audit for {website_url} is complete.

Please find your detailed audit report attached as a PDF.

Your audit includes:
✅ Overall SEO Score (0-100)
✅ Technical SEO analysis
✅ On-page optimization review
✅ Content gap analysis
✅ Performance insights
✅ Google Search Console data (if connected)
✅ Google Analytics insights (if connected)
✅ Prioritized recommendations with action items

═══════════════════════════════════════

NEXT STEPS:

I'd love to discuss how to implement these recommendations and create a 90-day roadmap for your digital growth.

Schedule a free 30-minute strategy call:
📧 Reply to this email
💼 Connect on LinkedIn: linkedin.com/in/punkaj

═══════════════════════════════════════

Want ongoing SEO support? I offer:
- SEO strategy & consulting
- Content creation & optimization
- Technical SEO implementation
- Monthly monitoring & reporting
- Digital marketing automation

Let's talk about how I can help you achieve your growth goals.

Best regards,
{self.sender_name}
SEO & Digital Marketing Consultant
20+ Years Experience
📧 {self.sender_email}
🌐 psdigital.io
        """.strip()
        
        return self._send_email(recipient_email, subject, body, pdf_attachment=pdf_path)
    
    def _send_email(self, recipient_email, subject, body, pdf_attachment=None):
        """Internal method to send email via SMTP with optional PDF attachment"""
        try:
            # Create message
            message = MIMEMultipart()
            message["From"] = f"{self.sender_name} <{self.sender_email}>"
            message["To"] = recipient_email
            message["Subject"] = subject
            
            # Add body
            message.attach(MIMEText(body, "plain"))
            
            # Add PDF attachment if provided
            if pdf_attachment and os.path.exists(pdf_attachment):
                with open(pdf_attachment, "rb") as pdf_file:
                    pdf_part = MIMEApplication(pdf_file.read(), _subtype="pdf")
                    pdf_part.add_header(
                        "Content-Disposition",
                        f"attachment; filename={os.path.basename(pdf_attachment)}"
                    )
                    message.attach(pdf_part)
            
            # Send email
            with smtplib.SMTP(self.smtp_server, self.smtp_port) as server:
                server.starttls()
                server.login(self.sender_email, self.sender_password)
                server.send_message(message)
            
            return True
            
        except Exception as e:
            st.error(f"Email sending failed: {e}")
            return False
