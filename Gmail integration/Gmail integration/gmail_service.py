"""
Gmail Service Module
Handles Gmail API authentication and email operations
"""

import os
import base64
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email import encoders

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

# Gmail API scopes - modify if you need more permissions
SCOPES = ['https://www.googleapis.com/auth/gmail.send']

class GmailService:
    """Gmail API Service class for sending emails"""
    
    def __init__(self, credentials_path='credentials.json', token_path='token.json'):
        """
        Initialize Gmail Service
        
        Args:
            credentials_path: Path to OAuth credentials JSON file
            token_path: Path to store/load user token
        """
        self.credentials_path = credentials_path
        self.token_path = token_path
        self.service = None
        self.creds = None
        
    def authenticate(self):
        """
        Authenticate with Gmail API using OAuth 2.0
        
        Returns:
            bool: True if authentication successful
        """
        # Check if token already exists
        if os.path.exists(self.token_path):
            self.creds = Credentials.from_authorized_user_file(self.token_path, SCOPES)
        
        # If no valid credentials, get new ones
        if not self.creds or not self.creds.valid:
            if self.creds and self.creds.expired and self.creds.refresh_token:
                self.creds.refresh(Request())
            else:
                if not os.path.exists(self.credentials_path):
                    raise FileNotFoundError(
                        f"Credentials file not found: {self.credentials_path}\n"
                        "Please download credentials.json from Google Cloud Console."
                    )
                flow = InstalledAppFlow.from_client_secrets_file(
                    self.credentials_path, SCOPES
                )
                self.creds = flow.run_local_server(port=0)
            
            # Save token for future use
            with open(self.token_path, 'w') as token:
                token.write(self.creds.to_json())
        
        # Build Gmail service
        self.service = build('gmail', 'v1', credentials=self.creds)
        return True
    
    def create_message(self, to, subject, body, html=False):
        """
        Create an email message
        
        Args:
            to: Recipient email address
            subject: Email subject
            body: Email body content
            html: If True, body is treated as HTML
            
        Returns:
            dict: Message ready to be sent
        """
        if html:
            message = MIMEMultipart('alternative')
            message['to'] = to
            message['subject'] = subject
            html_part = MIMEText(body, 'html')
            message.attach(html_part)
        else:
            message = MIMEText(body)
            message['to'] = to
            message['subject'] = subject
        
        # Encode message
        raw = base64.urlsafe_b64encode(message.as_bytes()).decode()
        return {'raw': raw}
    
    def create_message_with_attachment(self, to, subject, body, attachment_path):
        """
        Create an email message with attachment
        
        Args:
            to: Recipient email address
            subject: Email subject
            body: Email body content
            attachment_path: Path to attachment file
            
        Returns:
            dict: Message ready to be sent
        """
        message = MIMEMultipart()
        message['to'] = to
        message['subject'] = subject
        
        # Add body
        message.attach(MIMEText(body, 'plain'))
        
        # Add attachment
        if os.path.exists(attachment_path):
            filename = os.path.basename(attachment_path)
            with open(attachment_path, 'rb') as f:
                part = MIMEBase('application', 'octet-stream')
                part.set_payload(f.read())
            encoders.encode_base64(part)
            part.add_header('Content-Disposition', f'attachment; filename="{filename}"')
            message.attach(part)
        
        raw = base64.urlsafe_b64encode(message.as_bytes()).decode()
        return {'raw': raw}
    
    def send_email(self, to, subject, body, html=False):
        """
        Send an email
        
        Args:
            to: Recipient email address
            subject: Email subject
            body: Email body content
            html: If True, body is treated as HTML
            
        Returns:
            dict: Sent message details or None if failed
        """
        if not self.service:
            raise Exception("Not authenticated. Call authenticate() first.")
        
        try:
            message = self.create_message(to, subject, body, html)
            sent_message = self.service.users().messages().send(
                userId='me', body=message
            ).execute()
            print(f"Email sent successfully! Message ID: {sent_message['id']}")
            return sent_message
        except HttpError as error:
            print(f"An error occurred: {error}")
            return None
    
    def send_email_with_attachment(self, to, subject, body, attachment_path):
        """
        Send an email with attachment
        
        Args:
            to: Recipient email address
            subject: Email subject
            body: Email body content
            attachment_path: Path to attachment file
            
        Returns:
            dict: Sent message details or None if failed
        """
        if not self.service:
            raise Exception("Not authenticated. Call authenticate() first.")
        
        try:
            message = self.create_message_with_attachment(to, subject, body, attachment_path)
            sent_message = self.service.users().messages().send(
                userId='me', body=message
            ).execute()
            print(f"Email with attachment sent successfully! Message ID: {sent_message['id']}")
            return sent_message
        except HttpError as error:
            print(f"An error occurred: {error}")
            return None


def quick_send(to, subject, body, html=False):
    """
    Quick function to send an email without managing service instance
    
    Args:
        to: Recipient email address
        subject: Email subject
        body: Email body content
        html: If True, body is treated as HTML
        
    Returns:
        dict: Sent message details or None if failed
    """
    gmail = GmailService()
    gmail.authenticate()
    return gmail.send_email(to, subject, body, html)
