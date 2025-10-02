# mailer.py
import smtplib
import ssl
import logging
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.header import Header
from email.utils import parseaddr, formataddr, formatdate, make_msgid
from flask import current_app

def _bool(v):
    return str(v).strip().lower() in {"1", "true", "yes", "on"}

def _addr_header(value: str) -> tuple[str, str]:
    """
    Recebe algo como 'Nome com Acento — <user@dominio>'
    Retorna (header_formatado_para_From_To, email_puro_para_envelope)
    """
    name, addr = parseaddr(value or "")
    if not addr:
        # se vier só o e-mail sem nome
        addr = (value or "").strip()
        name = ""
    header = formataddr((str(Header(name or "", "utf-8")), addr))
    return header, addr

def enviar_email(destinatarios, assunto, mensagem_html, timeout=30) -> bool:
    """
    Envia e-mail usando configurações do Flask:
      MAIL_ENABLED, MAIL_SERVER, MAIL_PORT, MAIL_USE_TLS, MAIL_USE_SSL,
      MAIL_USERNAME, MAIL_PASSWORD, MAIL_DEFAULT_SENDER
    Retorna True/False.
    """
    cfg = current_app.config

    if not _bool(cfg.get("MAIL_ENABLED", True)):
        logging.warning("[mail] envio desativado (MAIL_ENABLED=0).")
        return False

    smtp_server = cfg.get("MAIL_SERVER") or ""
    porta = int(cfg.get("MAIL_PORT") or 0)
    use_tls = _bool(cfg.get("MAIL_USE_TLS", False))
    use_ssl = _bool(cfg.get("MAIL_USE_SSL", False))
    username = cfg.get("MAIL_USERNAME") or ""
    password = cfg.get("MAIL_PASSWORD") or ""
    default_sender = cfg.get("MAIL_DEFAULT_SENDER") or (username or "noreply@example.com")

    if not smtp_server or not porta:
        logging.error("[mail] servidor SMTP não configurado (MAIL_SERVER/MAIL_PORT).")
        return False

    # Correções comuns: porta 465 => SSL implícito | porta 587 => STARTTLS
    if porta == 465 and use_tls and not use_ssl:
        logging.warning("[mail] Porta 465 com STARTTLS; ajustando para SSL.")
        use_tls, use_ssl = False, True
    if porta == 587 and use_ssl and not use_tls:
        logging.warning("[mail] Porta 587 com SSL; ajustando para STARTTLS.")
        use_tls, use_ssl = True, False

    # Normaliza destinatários
    if isinstance(destinatarios, str):
        destinatarios = [destinatarios]
    destinatarios = [d for d in destinatarios if d]

    if not destinatarios:
        logging.error("[mail] nenhum destinatário informado.")
        return False

    # Cabeçalhos (UTF-8 seguro)
    from_header, envelope_from = _addr_header(default_sender)
    to_headers = []
    envelope_rcpts = []
    for d in destinatarios:
        h, a = _addr_header(d)
        to_headers.append(h)
        envelope_rcpts.append(a)

    # Monta mensagem MIME (UTF-8)
    msg = MIMEMultipart('alternative')
    msg['From'] = from_header
    msg['To'] = ', '.join(to_headers)
    msg['Subject'] = str(Header(assunto or "", 'utf-8'))
    msg['Date'] = formatdate(localtime=True)
    msg['Message-ID'] = make_msgid()
    msg.attach(MIMEText(mensagem_html or "", 'html', _charset="utf-8"))

    # Envia
    try:
        if use_ssl:
            context = ssl.create_default_context()
            server = smtplib.SMTP_SSL(smtp_server, porta, timeout=timeout, context=context)
            server.ehlo()
        else:
            server = smtplib.SMTP(smtp_server, porta, timeout=timeout)
            server.ehlo()
            if use_tls:
                server.starttls()  # STARTTLS
                server.ehlo()

        if username:
            server.login(username, password)

        # IMPORTANTE: usar as_bytes() para não forçar ASCII
        server.sendmail(envelope_from, envelope_rcpts, msg.as_bytes())
        server.quit()
        logging.info(f"[mail] enviado para {envelope_rcpts} (porta={porta}, TLS={use_tls}, SSL={use_ssl})")
        return True

    except Exception as e:
        logging.error(f"[mail] erro ao enviar e-mail: {e}", exc_info=True)
        return False
