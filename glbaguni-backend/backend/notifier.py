import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import Optional, List
import logging
from datetime import datetime

# Handle relative imports for both module and script execution
try:
    from .models import EmailNotification, ArticleSummary
    from .config import settings
except ImportError:
    from models import EmailNotification, ArticleSummary
    from config import settings

logger = logging.getLogger(__name__)

class EmailNotifier:
    """Handles email notifications using SMTP (easily replaceable with Mailgun)."""
    
    def __init__(self):
        self.smtp_host = settings.SMTP_HOST
        self.smtp_port = settings.SMTP_PORT
        self.smtp_username = settings.SMTP_USERNAME
        self.smtp_password = settings.SMTP_PASSWORD
        self.smtp_use_tls = settings.SMTP_USE_TLS
        
        # Log SMTP configuration for debugging
        logger.info("🔍 SMTP Configuration Debug:")
        logger.info(f"  SMTP_HOST: {self.smtp_host}")
        logger.info(f"  SMTP_PORT: {self.smtp_port}")
        logger.info(f"  SMTP_USERNAME: {'✅ SET' if self.smtp_username else '❌ NOT SET'}")
        logger.info(f"  SMTP_PASSWORD: {'✅ SET' if self.smtp_password else '❌ NOT SET'}")
        logger.info(f"  SMTP_USE_TLS: {self.smtp_use_tls}")
        
        if not self.smtp_username or not self.smtp_password:
            error_msg = "SMTP username and password are required"
            logger.error(f"❌ {error_msg}")
            logger.error("💡 Please check your .env file and ensure SMTP_USERNAME and SMTP_PASSWORD are set")
            logger.error("💡 For Gmail, you need to:")
            logger.error("   1. Enable 2-Factor Authentication")
            logger.error("   2. Generate an App Password")
            logger.error("   3. Use the App Password as SMTP_PASSWORD")
            raise ValueError(error_msg)
    
    def send_email(self, notification: EmailNotification) -> bool:
        """Send an email notification."""
        try:
            # Create message
            msg = MIMEMultipart('alternative')
            msg['From'] = self.smtp_username
            msg['To'] = notification.recipient
            msg['Subject'] = notification.subject
            
            # Add plain text and HTML parts
            text_part = MIMEText(notification.body, 'plain', 'utf-8')
            msg.attach(text_part)
            
            if notification.html_body:
                html_part = MIMEText(notification.html_body, 'html', 'utf-8')
                msg.attach(html_part)
            
            # Send email
            with smtplib.SMTP(self.smtp_host, self.smtp_port) as server:
                if self.smtp_use_tls:
                    server.starttls()
                
                server.login(self.smtp_username, self.smtp_password)
                server.send_message(msg)
            
            logger.info(f"Email sent successfully to {notification.recipient}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to send email to {notification.recipient}: {e}")
            return False
    
    def create_summary_email_content(self, summaries: List[ArticleSummary]) -> tuple[str, str]:
        """Create email content from article summaries."""
        if not summaries:
            return "No articles to summarize", ""
        
        # Plain text version
        plain_text = f"📰 글바구니 요약 리포트\n\n"
        plain_text += f"총 {len(summaries)}개의 기사를 요약했습니다.\n\n"
        
        for i, summary in enumerate(summaries, 1):
            plain_text += f"{i}. {summary.title}\n"
            plain_text += f"   출처: {summary.source}\n"
            plain_text += f"   요약: {summary.summary}\n"
            plain_text += f"   원문: {summary.url}\n\n"
        
        # HTML version
        html_content = f"""
        <html>
        <head>
            <style>
                body {{ font-family: Arial, sans-serif; line-height: 1.6; }}
                .header {{ background-color: #f8f9fa; padding: 20px; text-align: center; }}
                .article {{ margin: 20px 0; padding: 15px; border-left: 4px solid #007bff; }}
                .title {{ font-weight: bold; color: #333; }}
                .source {{ color: #666; font-size: 0.9em; }}
                .summary {{ margin: 10px 0; }}
                .link {{ color: #007bff; text-decoration: none; }}
            </style>
        </head>
        <body>
            <div class="header">
                <h1>📰 글바구니 요약 리포트</h1>
                <p>총 {len(summaries)}개의 기사를 요약했습니다.</p>
            </div>
        """
        
        for i, summary in enumerate(summaries, 1):
            html_content += f"""
            <div class="article">
                <div class="title">{i}. {summary.title}</div>
                <div class="source">출처: {summary.source}</div>
                <div class="summary">{summary.summary}</div>
                <a href="{summary.url}" class="link">원문 보기</a>
            </div>
            """
        
        html_content += "</body></html>"
        
        return plain_text, html_content
    
    def send_summary_email(self, recipient: str, summaries: List[ArticleSummary], 
                          custom_subject: Optional[str] = None) -> bool:
        """Send a summary email with article summaries."""
        try:
            if not summaries:
                logger.warning("No summaries to send")
                return False
            
            # Create email content
            plain_text, html_content = self.create_summary_email_content(summaries)
            
            # Create subject
            subject = custom_subject or f"📰 글바구니 요약 리포트 ({len(summaries)}개 기사)"
            
            # Create notification
            notification = EmailNotification(
                recipient=recipient,
                subject=subject,
                body=plain_text,
                html_body=html_content
            )
            
            return self.send_email(notification)
            
        except Exception as e:
            logger.error(f"Error creating summary email: {e}")
            return False
    
    def send_test_email(self, recipient: str) -> bool:
        """Send a test email to verify SMTP configuration."""
        try:
            notification = EmailNotification(
                recipient=recipient,
                subject="글바구니 테스트 이메일",
                body="이 이메일은 글바구니 시스템이 정상적으로 작동하는지 확인하기 위한 테스트 이메일입니다.",
                html_body=f"""
                <html>
                <body>
                    <h2>글바구니 테스트 이메일</h2>
                    <p>이 이메일은 글바구니 시스템이 정상적으로 작동하는지 확인하기 위한 테스트 이메일입니다.</p>
                    <p>발송 시간: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}</p>
                </body>
                </html>
                """
            )
            
            return self.send_email(notification)
            
        except Exception as e:
            logger.error(f"Error sending test email: {e}")
            return False

class MailgunNotifier:
    """Alternative email notifier using Mailgun API (for future use)."""
    
    def __init__(self, api_key: str, domain: str):
        self.api_key = api_key
        self.domain = domain
        self.base_url = f"https://api.mailgun.net/v3/{domain}"
    
    def send_email(self, notification: EmailNotification) -> bool:
        """Send email using Mailgun API."""
        # Implementation for Mailgun would go here
        # This is a placeholder for future implementation
        logger.info("Mailgun notifier not implemented yet")
        return False
