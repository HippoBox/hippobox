# ruff: noqa: E501
from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from enum import StrEnum
from html import escape


@dataclass(frozen=True)
class EmailContent:
    subject: str
    text: str
    html: str


@dataclass(frozen=True)
class TemplateCopy:
    subject: str
    preheader: str
    heading: str
    intro: str
    cta_label: str
    outro: str
    footer: str


@dataclass(frozen=True)
class TemplateTheme:
    page_bg: str
    panel_bg: str
    panel_border: str
    text_primary: str
    text_secondary: str
    cta_bg: str
    cta_fg: str
    muted_bg: str
    muted_fg: str


class EmailLocale(StrEnum):
    EN = "en"
    KO = "ko"


DEFAULT_LOCALE = EmailLocale.EN.value
SUPPORTED_LOCALES = {locale.value for locale in EmailLocale}

FRONTEND_LIGHT_THEME = TemplateTheme(
    page_bg="#f5f7fb",
    panel_bg="#ffffff",
    panel_border="#e4e7ec",
    text_primary="#132033",
    text_secondary="#4a5a6b",
    cta_bg="#101010",
    cta_fg="#f7f7f7",
    muted_bg="#f5f5f6",
    muted_fg="#4a5a6b",
)

TEMPLATE_COPY_BY_LOCALE: dict[str, dict[str, TemplateCopy]] = {
    "en": {
        "verification": TemplateCopy(
            subject="Verify your email",
            preheader="Confirm your email to finish setting up your account.",
            heading="Confirm your email",
            intro="Hi {name}, welcome aboard. Please verify your email to continue.",
            cta_label="Verify email",
            outro=(
                "This link is valid for a limited time. If you did not request this email, "
                "you can ignore it."
            ),
            footer="",
        ),
        "password_reset": TemplateCopy(
            subject="Reset your password",
            preheader="Reset your password with a secure one-time link.",
            heading="Reset your password",
            intro="Hi {name}, we received a request to reset your password.",
            cta_label="Reset password",
            outro=("If you did not request a password reset, you can safely ignore this email."),
            footer="For account security, never share this link with anyone.",
        ),
    },
    "ko": {
        "verification": TemplateCopy(
            subject="이메일을 인증해 주세요",
            preheader="계정 설정을 완료하려면 이메일 인증이 필요합니다.",
            heading="이메일 인증",
            intro="{name}님, 가입을 환영합니다. 계속하려면 이메일을 인증해 주세요.",
            cta_label="이메일 인증하기",
            outro=(
                "이 링크는 일정 시간 동안만 유효합니다. 요청하지 않은 메일이라면 무시해도 됩니다."
            ),
            footer="",
        ),
        "password_reset": TemplateCopy(
            subject="비밀번호를 재설정해 주세요",
            preheader="보안 일회성 링크로 비밀번호를 재설정할 수 있습니다.",
            heading="비밀번호 재설정",
            intro="{name}님, 비밀번호 재설정 요청을 확인했습니다.",
            cta_label="비밀번호 재설정",
            outro="요청하지 않은 재설정 메일이라면 무시해도 됩니다.",
            footer="계정 보안을 위해 이 링크를 다른 사람과 공유하지 마세요.",
        ),
    },
}


def _display_name(name: str | None) -> str:
    value = (name or "").strip()
    return value if value else "there"


def resolve_locale(language: str | None) -> str:
    if not language:
        return DEFAULT_LOCALE

    # Accept-Language can contain priority list like "ko-KR,ko;q=0.9,en;q=0.8".
    primary = language.split(",")[0].strip().lower()
    normalized = primary.split("-")[0]
    if normalized in SUPPORTED_LOCALES:
        return normalized
    return DEFAULT_LOCALE


def _copy(template_name: str, *, locale: str) -> TemplateCopy:
    return TEMPLATE_COPY_BY_LOCALE[locale][template_name]


def _verification_text_en(display_name: str, link: str) -> tuple[str, str]:
    text = (
        f"Hi {display_name},\n\n"
        "Please verify your email by clicking the link below:\n"
        f"{link}\n\n"
        "If you did not request this email, you can ignore it.\n"
    )
    manual_link_label = "If the button does not work, use this link:"
    return text, manual_link_label


def _verification_text_ko(display_name: str, link: str) -> tuple[str, str]:
    text = (
        f"{display_name}님, 안녕하세요.\n\n"
        "아래 링크를 눌러 이메일 인증을 완료해 주세요.\n"
        f"{link}\n\n"
        "요청하지 않은 메일이라면 무시하셔도 됩니다.\n"
    )
    manual_link_label = "버튼이 동작하지 않으면 아래 링크를 사용해 주세요:"
    return text, manual_link_label


def _password_reset_text_en(display_name: str, link: str) -> tuple[str, str]:
    text = (
        f"Hi {display_name},\n\n"
        "We received a request to reset your password. Use the link below:\n"
        f"{link}\n\n"
        "If you did not request a password reset, you can ignore this email.\n"
    )
    manual_link_label = "If the button does not work, use this link:"
    return text, manual_link_label


def _password_reset_text_ko(display_name: str, link: str) -> tuple[str, str]:
    text = (
        f"{display_name}님, 안녕하세요.\n\n"
        "비밀번호 재설정 요청을 확인했습니다. 아래 링크를 사용해 주세요.\n"
        f"{link}\n\n"
        "요청하지 않은 메일이라면 무시하셔도 됩니다.\n"
    )
    manual_link_label = "버튼이 동작하지 않으면 아래 링크를 사용해 주세요:"
    return text, manual_link_label


TextBuilder = Callable[[str, str], tuple[str, str]]
VERIFICATION_TEXT_BUILDERS: dict[str, TextBuilder] = {
    EmailLocale.EN.value: _verification_text_en,
    EmailLocale.KO.value: _verification_text_ko,
}
PASSWORD_RESET_TEXT_BUILDERS: dict[str, TextBuilder] = {
    EmailLocale.EN.value: _password_reset_text_en,
    EmailLocale.KO.value: _password_reset_text_ko,
}


def _build_email_html(
    *,
    app_name: str,
    preheader: str,
    heading: str,
    intro: str,
    cta_label: str,
    link: str,
    outro: str,
    footer: str,
    manual_link_label: str,
    theme: TemplateTheme,
    locale: str,
    code: str | None = None,
) -> str:
    # Mail is self-contained: inline styles, system fonts and presentation tables.
    app_name, preheader, heading, intro, cta_label, link, outro, footer, manual_link_label = (
        escape(value, quote=True)
        for value in (
            app_name,
            preheader,
            heading,
            intro,
            cta_label,
            link,
            outro,
            footer,
            manual_link_label,
        )
    )
    footer_html = (
        f'<p style="margin:12px 0 0;font-size:12px;line-height:1.6;color:{theme.text_secondary};">{footer}</p>'
        if footer.strip()
        else ""
    )
    if code is not None:
        action_html = (
            f'<p style="margin:0 0 24px;padding:20px 12px;border:1px solid {theme.panel_border};'
            f"border-radius:8px;background-color:{theme.muted_bg};color:{theme.text_primary};"
            f"font-family:monospace;font-size:32px;line-height:1.4;letter-spacing:6px;"
            f'font-weight:600;text-align:center;">{escape(code)}</p>'
        )
        fallback_html = ""
    else:
        action_html = f"""            <table role="presentation" cellpadding="0" cellspacing="0" border="0" style="margin:0 0 24px;">
              <tr><td align="center" bgcolor="{theme.cta_bg}" style="border-radius:999px;background-color:{theme.cta_bg};mso-padding-alt:12px 24px;">
                <a href="{link}" style="display:inline-block;padding:12px 24px;border:1px solid {theme.cta_bg};border-radius:999px;background-color:{theme.cta_bg};color:{theme.cta_fg};font-size:14px;font-weight:500;line-height:20px;text-decoration:none;text-align:center;">{cta_label}</a>
              </td></tr>
            </table>
"""
        fallback_html = f"""            <div style="margin-top:24px;padding-top:16px;border-top:1px solid {theme.panel_border};">
              <p style="margin:0 0 8px;font-size:12px;line-height:1.5;color:{theme.text_secondary};">{manual_link_label}</p>
              <a href="{link}" style="font-size:12px;line-height:1.6;color:{theme.text_secondary};text-decoration:underline;word-break:break-all;overflow-wrap:anywhere;">{link}</a>
            </div>
"""
    return f"""<!doctype html>
<html lang="{locale}">
  <head>
    <meta charset="utf-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1" />
    <title>{heading}</title>
  </head>
  <body style="margin:0;padding:0;background-color:{theme.page_bg};color:{theme.text_primary};font-family:Arial,'Apple SD Gothic Neo','Malgun Gothic',sans-serif;">
    <div style="display:none;visibility:hidden;opacity:0;max-height:0;overflow:hidden;mso-hide:all;">{preheader}</div>
    <table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0" style="background-color:{theme.page_bg};">
      <tr><td align="center" style="padding:24px 12px;">
        <table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0" style="max-width:480px;table-layout:fixed;background-color:{theme.panel_bg};border:1px solid {theme.panel_border};border-radius:16px;">
          <tr><td style="padding:24px 24px 0;font-size:13px;font-weight:600;line-height:1.5;color:{theme.text_primary};overflow-wrap:anywhere;">{app_name}</td></tr>
          <tr><td style="padding:24px;">
            <h1 style="margin:0 0 12px;font-size:22px;font-weight:500;line-height:1.35;color:{theme.text_primary};">{heading}</h1>
            <p style="margin:0 0 24px;font-size:14px;line-height:1.6;color:{theme.text_secondary};">{intro}</p>
            {action_html}
            <table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0">
              <tr><td style="padding:12px 14px;border-radius:8px;background-color:{theme.muted_bg};font-size:12px;line-height:1.6;color:{theme.muted_fg};">{outro}</td></tr>
            </table>
            {footer_html}
            {fallback_html}
          </td></tr>
        </table>
      </td></tr>
    </table>
  </body>
</html>
"""


def build_verification_email(
    *,
    name: str | None,
    link: str,
    app_name: str = "B4A",
    language: str | None = None,
) -> EmailContent:
    locale = resolve_locale(language)
    copy = _copy("verification", locale=locale)
    display_name = _display_name(name)
    text, manual_link_label = VERIFICATION_TEXT_BUILDERS[locale](display_name, link)
    html = _build_email_html(
        app_name=app_name,
        preheader=copy.preheader,
        heading=copy.heading,
        intro=copy.intro.format(name=display_name),
        cta_label=copy.cta_label,
        link=link,
        outro=copy.outro,
        footer=copy.footer,
        manual_link_label=manual_link_label,
        theme=FRONTEND_LIGHT_THEME,
        locale=locale,
    )
    return EmailContent(subject=copy.subject, text=text, html=html)


def build_password_reset_email(
    *,
    name: str | None,
    link: str,
    app_name: str = "B4A",
    language: str | None = None,
) -> EmailContent:
    locale = resolve_locale(language)
    copy = _copy("password_reset", locale=locale)
    display_name = _display_name(name)
    text, manual_link_label = PASSWORD_RESET_TEXT_BUILDERS[locale](display_name, link)
    html = _build_email_html(
        app_name=app_name,
        preheader=copy.preheader,
        heading=copy.heading,
        intro=copy.intro.format(name=display_name),
        cta_label=copy.cta_label,
        link=link,
        outro=copy.outro,
        footer=copy.footer,
        manual_link_label=manual_link_label,
        theme=FRONTEND_LIGHT_THEME,
        locale=locale,
    )
    return EmailContent(subject=copy.subject, text=text, html=html)


def build_welcome_email(
    *,
    name: str | None,
    link: str,
    app_name: str = "B4A",
    language: str | None = None,
) -> EmailContent:
    locale = resolve_locale(language)
    display_name = _display_name(name)
    if locale == "ko":
        heading = "환영합니다!"
        intro = f"{display_name}님, {app_name}에 오신 것을 환영합니다. 계정 생성이 완료되었습니다."
        cta = "시작하기"
        outro = "계정 설정에서 이름과 프로필 사진을 변경할 수 있습니다."
        manual = "아래 링크로도 시작할 수 있습니다."
    else:
        heading = "Welcome!"
        intro = f"Hi {display_name}, welcome to {app_name}. Your account is ready."
        cta = "Get started"
        outro = "You can update your name and profile photo in account settings."
        manual = "You can also get started using this link."
    html = _build_email_html(
        app_name=app_name,
        preheader=intro,
        heading=heading,
        intro=intro,
        cta_label=cta,
        link=link,
        outro=outro,
        footer="",
        manual_link_label=manual,
        theme=FRONTEND_LIGHT_THEME,
        locale=locale,
    )
    return EmailContent(subject=heading, text=f"{intro}\n\n{outro}\n\n{cta}: {link}", html=html)


def build_account_deletion_email(
    *,
    name: str | None,
    code: str,
    app_name: str = "B4A",
    language: str | None = None,
) -> EmailContent:
    locale = resolve_locale(language)
    display_name = _display_name(name)
    if locale == "ko":
        subject = "계정 삭제 인증 코드"
        intro = f"{display_name}님, {app_name} 계정 삭제를 요청하셨습니다. 아래 코드는 10분 동안 유효합니다."
        warning = "이 코드를 입력하고 삭제를 확정하면 계정과 연결된 데이터가 영구적으로 삭제됩니다. 요청하지 않았다면 코드를 공유하거나 입력하지 마세요."
    else:
        subject = "Confirm account deletion"
        intro = f"Hi {display_name}, you requested deletion of your {app_name} account. This code expires in 10 minutes."
        warning = "Entering this code and confirming deletion permanently removes your account and associated data. If you did not request this, do not share or enter this code."
    # A code-only email has no action URL, so opening a mail client cannot delete an account.
    html = _build_email_html(
        app_name=app_name,
        preheader=intro,
        heading=subject,
        intro=intro,
        cta_label="",
        link="",
        outro=warning,
        footer="",
        manual_link_label="",
        theme=FRONTEND_LIGHT_THEME,
        locale=locale,
        code=code,
    )
    return EmailContent(subject=subject, text=f"{intro}\n\n{code}\n\n{warning}", html=html)


def build_password_change_email(
    *,
    name: str | None,
    code: str,
    app_name: str = "B4A",
    language: str | None = None,
) -> EmailContent:
    locale = resolve_locale(language)
    display_name = _display_name(name)
    if locale == "ko":
        subject = "비밀번호 변경 인증 코드"
        intro = f"{display_name}님, {app_name} 비밀번호 변경을 요청하셨습니다. 아래 코드는 10분 동안 유효합니다."
        warning = "이 코드를 입력하면 새 비밀번호를 저장할 수 있습니다. 요청하지 않았다면 코드를 공유하거나 입력하지 마세요."
    else:
        subject = "Confirm password change"
        intro = f"Hi {display_name}, you requested a password change for your {app_name} account. This code expires in 10 minutes."
        warning = "Use this code to confirm your new password. If you did not request this, do not share or enter this code."
    # A code-only email has no action URL, so opening a mail client cannot change a password.
    html = _build_email_html(
        app_name=app_name,
        preheader=intro,
        heading=subject,
        intro=intro,
        cta_label="",
        link="",
        outro=warning,
        footer="",
        manual_link_label="",
        theme=FRONTEND_LIGHT_THEME,
        locale=locale,
        code=code,
    )
    return EmailContent(subject=subject, text=f"{intro}\n\n{code}\n\n{warning}", html=html)


def build_lifecycle_email(
    *, kind: str, name: str, plan: str, link: str, app_name: str, language: str = "en"
) -> EmailContent:
    locale = resolve_locale(language)
    headings = {
        "subscription_started": ("구독을 시작했습니다", "Your subscription has started"),
        "plan_changed": ("요금제를 변경했습니다", "Your plan has changed"),
        "account_deleted": ("계정을 삭제했습니다", "Your account has been deleted"),
    }
    heading = headings[kind][0 if locale == "ko" else 1]
    if locale == "ko":
        intro = f"{_display_name(name)}님, {heading}."
        outro = (
            f"현재 요금제: {plan}"
            if kind != "account_deleted"
            else "계정 삭제가 완료되었습니다. 이용해 주셔서 감사합니다."
        )
        cta, manual = "서비스 열기", "아래 주소에서도 확인할 수 있습니다."
    else:
        intro = f"Hi {_display_name(name)}, {heading.lower()}."
        outro = (
            f"Current plan: {plan}"
            if kind != "account_deleted"
            else "Account deletion is complete. Thank you for using our service."
        )
        cta, manual = "Open service", "You can also use this address."
    html = _build_email_html(
        app_name=app_name,
        preheader=heading,
        heading=heading,
        intro=intro,
        cta_label=cta,
        link=link,
        outro=outro,
        footer="",
        manual_link_label=manual,
        theme=FRONTEND_LIGHT_THEME,
        locale=locale,
    )
    return EmailContent(subject=heading, text=f"{intro}\n\n{outro}\n\n{link}", html=html)
