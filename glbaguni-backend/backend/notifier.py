import logging
import smtplib
from datetime import datetime
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from typing import List, Optional
import os

# Handle relative imports for both module and script execution
try:
    from backend.models import ArticleSummary, EmailNotification
    from backend.config import settings
except ImportError:
    try:
        from models import ArticleSummary, EmailNotification
        from config import settings
    except ImportError:
        from models import ArticleSummary, EmailNotification
        # Create fallback settings
        class Settings:
            SMTP_SERVER = os.getenv("SMTP_SERVER", "smtp.gmail.com")
            SMTP_PORT = int(os.getenv("SMTP_PORT", "587"))
            SMTP_USERNAME = os.getenv("SMTP_USERNAME", "")
            SMTP_PASSWORD = os.getenv("SMTP_PASSWORD", "")
            SMTP_USE_TLS = os.getenv("SMTP_USE_TLS", "true").lower() == "true"
        settings = Settings()

logger = logging.getLogger(__name__)


class EmailNotifier:
    """Handles email notifications using SMTP (easily replaceable with Mailgun)."""

    def __init__(self):
        # 환경변수에서 직접 가져오기 (안전한 방식)
        self.smtp_host = os.getenv("SMTP_SERVER", "smtp.gmail.com")
        self.smtp_port = int(os.getenv("SMTP_PORT", "587"))
        self.smtp_username = os.getenv("SMTP_USERNAME")
        self.smtp_password = os.getenv("SMTP_PASSWORD")
        self.smtp_use_tls = os.getenv("SMTP_USE_TLS", "true").lower() == "true"

        # Log SMTP configuration for debugging
        logger.info("🔍 SMTP Configuration Debug:")
        logger.info(f"  SMTP_HOST: {self.smtp_host}")
        logger.info(f"  SMTP_PORT: {self.smtp_port}")
        logger.info(
            f"  SMTP_USERNAME: {'✅ SET' if self.smtp_username else '❌ NOT SET'}"
        )
        logger.info(
            f"  SMTP_PASSWORD: {'✅ SET' if self.smtp_password else '❌ NOT SET'}"
        )
        logger.info(f"  SMTP_USE_TLS: {self.smtp_use_tls}")

        if not self.smtp_username or not self.smtp_password:
            error_msg = "SMTP username and password are required"
            logger.warning(f"⚠️ {error_msg}")
            logger.warning(
                "💡 Please check your .env file and ensure SMTP_USERNAME and SMTP_PASSWORD are set"
            )
            logger.warning("💡 For Gmail, you need to:")
            logger.warning("   1. Enable 2-Factor Authentication")
            logger.warning("   2. Generate an App Password")
            logger.warning("   3. Use the App Password as SMTP_PASSWORD")
            logger.warning("🔄 EmailNotifier가 비활성화됩니다 (서버는 계속 실행)")
            # raise 대신 warning으로 변경하여 서버가 계속 실행되도록
            self.smtp_username = ""
            self.smtp_password = ""

    def send_email(self, notification: EmailNotification) -> bool:
        """Send an email notification."""
        try:
            # SMTP 설정 검증
            if not self.smtp_username or not self.smtp_password:
                logger.error("SMTP 설정이 누락되어 이메일을 보낼 수 없습니다")
                return False
                
            # Create message
            msg = MIMEMultipart("alternative")
            msg["From"] = self.smtp_username
            msg["To"] = notification.recipient
            msg["Subject"] = notification.subject

            # Add plain text and HTML parts
            text_part = MIMEText(notification.body, "plain", "utf-8")
            msg.attach(text_part)

            if notification.html_body:
                html_part = MIMEText(notification.html_body, "html", "utf-8")
                msg.attach(html_part)

            # Send email
            with smtplib.SMTP(self.smtp_host or "smtp.gmail.com", self.smtp_port) as server:
                if self.smtp_use_tls:
                    server.starttls()

                server.login(self.smtp_username or "", self.smtp_password or "")
                server.send_message(msg)

            logger.info(f"Email sent successfully to {notification.recipient}")
            return True

        except Exception as e:
            logger.error(f"Failed to send email to {notification.recipient}: {e}")
            return False

    def create_summary_email_content(
        self, summaries: List[ArticleSummary]
    ) -> tuple[str, str]:
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

    def send_summary_email(
        self,
        recipient: str,
        summaries: List[ArticleSummary],
        custom_subject: Optional[str] = None,
    ) -> bool:
        """Send a summary email with article summaries."""
        try:
            if not summaries:
                logger.warning("No summaries to send")
                return False

            # Create email content
            plain_text, html_content = self.create_summary_email_content(summaries)

            # Create subject
            subject = (
                custom_subject or f"📰 글바구니 요약 리포트 ({len(summaries)}개 기사)"
            )

            # Create notification
            notification = EmailNotification(
                recipient=recipient,
                subject=subject,
                body=plain_text,
                html_body=html_content,
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
                """,
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
