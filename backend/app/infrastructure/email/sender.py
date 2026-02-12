"""Email sending service."""

import logging
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

import aiosmtplib

try:
    import resend

    RESEND_AVAILABLE = True
except ImportError:
    RESEND_AVAILABLE = False

from app.config import Settings

logger = logging.getLogger(__name__)


class EmailService:
    """Email sending service using Resend or SMTP."""

    def __init__(self, settings: Settings) -> None:
        self.host = settings.SMTP_HOST
        self.port = settings.SMTP_PORT
        self.user = settings.SMTP_USER
        self.password = settings.SMTP_PASSWORD
        self.from_email = settings.SMTP_FROM
        self.enabled = settings.FEATURE_EMAIL_NOTIFICATIONS
        self.frontend_url = settings.frontend_url
        self.resend_api_key = settings.RESEND_API_KEY

        # Configure Resend if API key is available
        if self.resend_api_key and RESEND_AVAILABLE:
            resend.api_key = self.resend_api_key
            self.use_resend = True
            logger.info("Email service configured with Resend")
        else:
            self.use_resend = False
            logger.info("Email service configured with SMTP")

    async def _send_email(self, to: str, subject: str, html_body: str) -> bool:
        """Send email via Resend or SMTP."""
        if not self.enabled:
            logger.info(f"Email notifications disabled. Would send to {to}: {subject}")
            return True

        if self.use_resend:
            return await self._send_via_resend(to, subject, html_body)
        else:
            return await self._send_via_smtp(to, subject, html_body)

    async def _send_via_resend(self, to: str, subject: str, html_body: str) -> bool:
        """Send email via Resend API."""
        try:
            params = {
                "from": self.from_email,
                "to": [to],
                "subject": subject,
                "html": html_body,
            }
            response = resend.Emails.send(params)
            logger.info(
                f"Email sent via Resend to {to}: {subject} (id: {response.get('id', 'unknown')})"
            )
            return True
        except Exception as e:
            logger.error(f"Failed to send email via Resend to {to}: {e}")
            return False

    async def _send_via_smtp(self, to: str, subject: str, html_body: str) -> bool:
        """Send email via SMTP."""
        try:
            message = MIMEMultipart("alternative")
            message["Subject"] = subject
            message["From"] = self.from_email
            message["To"] = to

            html_part = MIMEText(html_body, "html")
            message.attach(html_part)

            # Use STARTTLS for port 587 (OVH, Gmail, etc.)
            use_tls = self.port == 465
            start_tls = self.port == 587

            await aiosmtplib.send(
                message,
                hostname=self.host,
                port=self.port,
                username=self.user if self.user else None,
                password=self.password if self.password else None,
                use_tls=use_tls,
                start_tls=start_tls,
            )

            logger.info(f"Email sent via SMTP to {to}: {subject}")
            return True
        except Exception as e:
            logger.error(f"Failed to send email via SMTP to {to}: {e}")
            return False

    async def send_verification_email(self, to: str, token: str, name: str) -> bool:
        """Send email verification link."""
        subject = "Vérifiez votre adresse email - Bobby"
        verification_url = f"{self.frontend_url}/verify-email?token={token}"

        html_body = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="utf-8">
        </head>
        <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
            <div style="max-width: 600px; margin: 0 auto; padding: 20px;">
                <h1 style="color: #0ea5e9;">Bienvenue sur Bobby</h1>
                <p>Bonjour {name},</p>
                <p>Merci de vous être inscrit. Pour activer votre compte, veuillez cliquer sur le bouton ci-dessous :</p>
                <p style="text-align: center; margin: 30px 0;">
                    <a href="{verification_url}"
                       style="background-color: #0ea5e9; color: white; padding: 12px 30px;
                              text-decoration: none; border-radius: 5px; display: inline-block;">
                        Vérifier mon email
                    </a>
                </p>
                <p>Ou copiez ce lien dans votre navigateur :</p>
                <p style="word-break: break-all; color: #0ea5e9;">{verification_url}</p>
                <p>Ce lien expire dans 7 jours.</p>
                <hr style="border: none; border-top: 1px solid #eee; margin: 30px 0;">
                <p style="color: #666; font-size: 12px;">
                    Cet email a été envoyé par Bobby.
                    Si vous n'avez pas créé de compte, ignorez cet email.
                </p>
            </div>
        </body>
        </html>
        """

        return await self._send_email(to, subject, html_body)

    async def send_password_reset_email(self, to: str, token: str, name: str) -> bool:
        """Send password reset link."""
        subject = "Réinitialisation de votre mot de passe - Bobby"
        reset_url = f"{self.frontend_url}/reset-password?token={token}"

        html_body = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="utf-8">
        </head>
        <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
            <div style="max-width: 600px; margin: 0 auto; padding: 20px;">
                <h1 style="color: #0ea5e9;">Réinitialisation du mot de passe</h1>
                <p>Bonjour {name},</p>
                <p>Vous avez demandé la réinitialisation de votre mot de passe.
                   Cliquez sur le bouton ci-dessous pour créer un nouveau mot de passe :</p>
                <p style="text-align: center; margin: 30px 0;">
                    <a href="{reset_url}"
                       style="background-color: #0ea5e9; color: white; padding: 12px 30px;
                              text-decoration: none; border-radius: 5px; display: inline-block;">
                        Réinitialiser mon mot de passe
                    </a>
                </p>
                <p>Ou copiez ce lien dans votre navigateur :</p>
                <p style="word-break: break-all; color: #0ea5e9;">{reset_url}</p>
                <p><strong>Ce lien expire dans 1 heure.</strong></p>
                <p>Si vous n'avez pas demandé cette réinitialisation, ignorez cet email.
                   Votre mot de passe restera inchangé.</p>
                <hr style="border: none; border-top: 1px solid #eee; margin: 30px 0;">
                <p style="color: #666; font-size: 12px;">
                    Cet email a été envoyé par Bobby.
                </p>
            </div>
        </body>
        </html>
        """

        return await self._send_email(to, subject, html_body)

    async def send_magic_link_email(self, to: str, token: str, name: str) -> bool:
        """Send magic link for passwordless login."""
        subject = "Votre lien de connexion - Bobby"
        magic_url = f"{self.frontend_url}/auth/magic-link?token={token}"

        html_body = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="utf-8">
        </head>
        <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
            <div style="max-width: 600px; margin: 0 auto; padding: 20px;">
                <h1 style="color: #0ea5e9;">Connexion à Bobby</h1>
                <p>Bonjour {name},</p>
                <p>Cliquez sur le bouton ci-dessous pour vous connecter :</p>
                <p style="text-align: center; margin: 30px 0;">
                    <a href="{magic_url}"
                       style="background-color: #0ea5e9; color: white; padding: 12px 30px;
                              text-decoration: none; border-radius: 5px; display: inline-block;">
                        Se connecter
                    </a>
                </p>
                <p><strong>Ce lien expire dans 15 minutes et ne peut être utilisé qu'une fois.</strong></p>
                <hr style="border: none; border-top: 1px solid #eee; margin: 30px 0;">
                <p style="color: #666; font-size: 12px;">
                    Si vous n'avez pas demandé ce lien, ignorez cet email.
                </p>
            </div>
        </body>
        </html>
        """

        return await self._send_email(to, subject, html_body)

    async def send_cooptation_confirmation(
        self,
        to: str,
        name: str,
        candidate_name: str,
        opportunity_title: str,
    ) -> bool:
        """Send cooptation submission confirmation."""
        subject = "Confirmation de votre cooptation - Bobby"

        html_body = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="utf-8">
        </head>
        <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
            <div style="max-width: 600px; margin: 0 auto; padding: 20px;">
                <h1 style="color: #0ea5e9;">Cooptation enregistrée</h1>
                <p>Bonjour {name},</p>
                <p>Votre proposition de cooptation a bien été enregistrée :</p>
                <div style="background-color: #f3f4f6; padding: 15px; border-radius: 5px; margin: 20px 0;">
                    <p><strong>Candidat :</strong> {candidate_name}</p>
                    <p><strong>Opportunité :</strong> {opportunity_title}</p>
                </div>
                <p>Nous examinerons cette candidature et vous tiendrons informé de la suite.</p>
                <p>Merci pour votre contribution !</p>
                <hr style="border: none; border-top: 1px solid #eee; margin: 30px 0;">
                <p style="color: #666; font-size: 12px;">
                    Cet email a été envoyé par Bobby.
                </p>
            </div>
        </body>
        </html>
        """

        return await self._send_email(to, subject, html_body)

    async def send_cooptation_status_update(
        self,
        to: str,
        name: str,
        candidate_name: str,
        opportunity_title: str,
        new_status: str,
    ) -> bool:
        """Send cooptation status update notification."""
        status_labels = {
            "pending": "En attente",
            "in_review": "En cours d'examen",
            "interview": "En entretien",
            "accepted": "Accepté",
            "rejected": "Refusé",
        }
        status_label = status_labels.get(new_status, new_status)

        subject = f"Mise à jour de votre cooptation - {status_label}"

        status_color = "#f59e0b"  # warning/orange by default
        if new_status == "accepted":
            status_color = "#10b981"  # success/green
        elif new_status == "rejected":
            status_color = "#ef4444"  # error/red
        elif new_status == "interview":
            status_color = "#0ea5e9"  # primary/blue

        html_body = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="utf-8">
        </head>
        <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
            <div style="max-width: 600px; margin: 0 auto; padding: 20px;">
                <h1 style="color: #0ea5e9;">Mise à jour de votre cooptation</h1>
                <p>Bonjour {name},</p>
                <p>Le statut de votre cooptation a été mis à jour :</p>
                <div style="background-color: #f3f4f6; padding: 15px; border-radius: 5px; margin: 20px 0;">
                    <p><strong>Candidat :</strong> {candidate_name}</p>
                    <p><strong>Opportunité :</strong> {opportunity_title}</p>
                    <p><strong>Nouveau statut :</strong>
                       <span style="color: {status_color}; font-weight: bold;">{status_label}</span>
                    </p>
                </div>
                <p>Connectez-vous à votre espace pour plus de détails.</p>
                <hr style="border: none; border-top: 1px solid #eee; margin: 30px 0;">
                <p style="color: #666; font-size: 12px;">
                    Cet email a été envoyé par Bobby.
                </p>
            </div>
        </body>
        </html>
        """

        return await self._send_email(to, subject, html_body)

    async def send_invitation_email(
        self,
        to_email: str,
        token: str,
        role: str,
    ) -> bool:
        """Send invitation email to join the platform."""
        role_labels = {
            "user": "Consultant",
            "commercial": "Commercial",
            "rh": "Ressources Humaines",
            "admin": "Administrateur",
        }
        role_label = role_labels.get(role, role)

        subject = "Invitation à rejoindre Bobby"
        invitation_url = f"{self.frontend_url}/accept-invitation?token={token}"

        html_body = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="utf-8">
        </head>
        <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
            <div style="max-width: 600px; margin: 0 auto; padding: 20px;">
                <h1 style="color: #0ea5e9;">Vous êtes invité(e) !</h1>
                <p>Bonjour,</p>
                <p>Vous avez été invité(e) à rejoindre la plateforme <strong>Bobby</strong>
                   en tant que <strong style="color: #0ea5e9;">{role_label}</strong>.</p>
                <p>Cette plateforme vous permettra de proposer des candidats pour les opportunités
                   de notre entreprise et de suivre vos cooptations.</p>
                <p style="text-align: center; margin: 30px 0;">
                    <a href="{invitation_url}"
                       style="background-color: #0ea5e9; color: white; padding: 12px 30px;
                              text-decoration: none; border-radius: 5px; display: inline-block;">
                        Accepter l'invitation
                    </a>
                </p>
                <p>Ou copiez ce lien dans votre navigateur :</p>
                <p style="word-break: break-all; color: #0ea5e9;">{invitation_url}</p>
                <p><strong>Ce lien expire dans 48 heures.</strong></p>
                <hr style="border: none; border-top: 1px solid #eee; margin: 30px 0;">
                <p style="color: #666; font-size: 12px;">
                    Cet email a été envoyé par Bobby.
                    Si vous n'attendiez pas cette invitation, ignorez cet email.
                </p>
            </div>
        </body>
        </html>
        """

        return await self._send_email(to_email, subject, html_body)
