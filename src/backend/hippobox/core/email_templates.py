# flake8: noqa
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class EmailContent:
    subject: str
    text: str
    html: str


def _display_name(name: str | None) -> str:
    value = (name or "").strip()
    return value if value else "there"


def _build_email_html(
    *,
    preheader: str,
    heading: str,
    intro: str,
    cta_label: str,
    link: str,
    outro: str,
    footer: str,
) -> str:
    return f"""<!doctype html>
<html>
  <head>
    <meta charset="utf-8" />
    <meta name="viewport" content="width=device-width" />
    <title>{heading}</title>
  </head>
  <body style="margin:0;padding:0;background-color:#f6f4f1;color:#0f172a;">
    <span style="display:none;visibility:hidden;opacity:0;height:0;width:0;overflow:hidden;">
      {preheader}
    </span>
    <table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="background:#f6f4f1;">
      <tr>
        <td align="center" style="padding:32px 16px;">
          <table role="presentation" width="100%" cellpadding="0" cellspacing="0"
            style="max-width:560px;background:#ffffff;border-radius:26px;overflow:hidden;border:1px solid #e2e8f0;box-shadow:0 18px 45px rgba(15,23,42,0.08);">
            <tr>
              <td style="padding:28px 32px;background:linear-gradient(135deg,#111827 0%,#1f2937 55%,#334155 100%);">
                <div style="font-family:'Space Grotesk', 'Sora', ui-sans-serif, system-ui, -apple-system, 'Segoe UI', sans-serif;font-size:22px;font-weight:600;color:#f8fafc;">
                  HippoBox
                </div>
                <div style="margin-top:6px;font-family:'Sora', ui-sans-serif, system-ui, -apple-system, 'Segoe UI', sans-serif;font-size:13px;letter-spacing:0.06em;text-transform:uppercase;color:#cbd5f5;">
                  Personal knowledge, beautifully organized
                </div>
              </td>
            </tr>
            <tr>
              <td style="padding:32px;">
                <h1 style="margin:0 0 12px;font-family:'Space Grotesk', 'Sora', ui-sans-serif, system-ui, -apple-system, 'Segoe UI', sans-serif;font-size:24px;line-height:1.2;color:#0f172a;">
                  {heading}
                </h1>
                <p style="margin:0 0 20px;font-family:'Sora', ui-sans-serif, system-ui, -apple-system, 'Segoe UI', sans-serif;font-size:15px;line-height:1.6;color:#334155;">
                  {intro}
                </p>
                <table role="presentation" cellpadding="0" cellspacing="0" style="margin:0 0 24px;">
                  <tr>
                    <td align="left">
                      <a href="{link}"
                        style="display:inline-block;padding:12px 22px;border-radius:999px;background:linear-gradient(135deg,#111827 0%,#1f2937 55%,#334155 100%);color:#f8fafc;font-family:'Sora', ui-sans-serif, system-ui, -apple-system, 'Segoe UI', sans-serif;font-size:14px;font-weight:600;text-decoration:none;border:1px solid rgba(255,255,255,0.06);box-shadow:0 10px 20px rgba(15,23,42,0.18);">
                        {cta_label}
                      </a>
                    </td>
                  </tr>
                </table>
                <p style="margin:0 0 18px;font-family:'Sora', ui-sans-serif, system-ui, -apple-system, 'Segoe UI', sans-serif;font-size:14px;line-height:1.6;color:#475569;">
                  {outro}
                </p>
                <p style="margin:0 0 8px;font-family:'Sora', ui-sans-serif, system-ui, -apple-system, 'Segoe UI', sans-serif;font-size:13px;color:#64748b;">
                  If the button doesn't work, copy and paste this link:
                </p>
                <p style="margin:0;font-family:'Sora', ui-sans-serif, system-ui, -apple-system, 'Segoe UI', sans-serif;font-size:13px;line-height:1.6;">
                  <a href="{link}" style="color:#0f172a;text-decoration:none;word-break:break-all;">{link}</a>
                </p>
              </td>
            </tr>
            <tr>
              <td style="padding:18px 32px;background:#f1f5f9;font-family:'Sora', ui-sans-serif, system-ui, -apple-system, 'Segoe UI', sans-serif;font-size:12px;color:#64748b;">
                {footer}
              </td>
            </tr>
          </table>
        </td>
      </tr>
    </table>
  </body>
</html>
"""


def build_verification_email(*, name: str | None, link: str) -> EmailContent:
    display = _display_name(name)
    subject = "Verify your HippoBox email"
    text = (
        f"Hi {display},\n\n"
        "You're almost ready to start using HippoBox. Verify your email by clicking the link below:\n"
        f"{link}\n\n"
        "If you did not request this, you can ignore this email.\n"
    )
    html = _build_email_html(
        preheader="Confirm your HippoBox email to finish setting up your account.",
        heading="Confirm your email",
        intro=f"Hi {display}, you're almost ready to start capturing knowledge in HippoBox.",
        cta_label="Verify email",
        link=link,
        outro="This link is valid for a limited time. If you did not request this, you can ignore this email.",
        footer="Need help? Reply to this email and our team will assist you.",
    )
    return EmailContent(subject=subject, text=text, html=html)


def build_password_reset_email(*, name: str | None, link: str) -> EmailContent:
    display = _display_name(name)
    subject = "Reset your HippoBox password"
    text = (
        f"Hi {display},\n\n"
        "We received a request to reset your HippoBox password. Use the link below to continue:\n"
        f"{link}\n\n"
        "If you did not request this, you can ignore this email.\n"
    )
    html = _build_email_html(
        preheader="Reset your HippoBox password with a secure one-time link.",
        heading="Reset your password",
        intro=f"Hi {display}, we received a request to reset your HippoBox password.",
        cta_label="Reset password",
        link=link,
        outro="If you did not request a password reset, you can safely ignore this email.",
        footer="For account security, never share this link with anyone.",
    )
    return EmailContent(subject=subject, text=text, html=html)
