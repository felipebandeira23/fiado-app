"""
Serviço de notificação via WhatsApp.

Suporta dois provedores configuráveis via variáveis de ambiente:
  - Z-API  (padrão, recomendado para Brasil)
  - Twilio (alternativa internacional)

Variáveis de ambiente necessárias:
  WHATSAPP_PROVIDER = "zapi" | "twilio" | ""  (vazio = desabilitado)

  # Z-API
  ZAPI_INSTANCE_ID  = ID da instância Z-API
  ZAPI_TOKEN        = Token de autenticação Z-API
  ZAPI_CLIENT_TOKEN = Client-Token Z-API (opcional, header extra de segurança)

  # Twilio
  TWILIO_ACCOUNT_SID = SID da conta Twilio
  TWILIO_AUTH_TOKEN  = Auth token Twilio
  TWILIO_FROM_NUMBER = Número de origem (formato: whatsapp:+5511999999999)

Como usar:
    from apps.faturas.whatsapp import enviar_notificacao_fatura_fechada
    enviar_notificacao_fatura_fechada(fatura)

O módulo falha silenciosamente quando não configurado — nunca levanta exceções
que possam interromper o fluxo principal do sistema.
"""
import json
import logging
import urllib.request
import urllib.parse
import urllib.error
from base64 import b64encode

from django.conf import settings

logger = logging.getLogger(__name__)


def _get_setting(name, default=''):
    """Lê do settings ou do environ diretamente."""
    return getattr(settings, name, '') or default


def _prover_configurado():
    """Retorna o nome do provedor ativo, ou '' se desabilitado."""
    provider = _get_setting('WHATSAPP_PROVIDER', '').lower().strip()
    if provider == 'zapi':
        instance = _get_setting('ZAPI_INSTANCE_ID', '')
        token = _get_setting('ZAPI_TOKEN', '')
        if instance and token:
            return 'zapi'
    elif provider == 'twilio':
        sid = _get_setting('TWILIO_ACCOUNT_SID', '')
        auth = _get_setting('TWILIO_AUTH_TOKEN', '')
        from_num = _get_setting('TWILIO_FROM_NUMBER', '')
        if sid and auth and from_num:
            return 'twilio'
    return ''


def _formatar_telefone(telefone):
    """Remove caracteres não numéricos e garante código internacional brasileiro (55)."""
    digits = ''.join(c for c in telefone if c.isdigit())
    if not digits:
        return ''
    # Adicionar DDI 55 se não houver
    if not digits.startswith('55'):
        digits = '55' + digits
    return digits


def _enviar_zapi(numero, mensagem):
    """Envia mensagem via Z-API."""
    instance = _get_setting('ZAPI_INSTANCE_ID', '')
    token = _get_setting('ZAPI_TOKEN', '')
    client_token = _get_setting('ZAPI_CLIENT_TOKEN', '')

    url = f'https://api.z-api.io/instances/{instance}/token/{token}/send-text'
    payload = json.dumps({'phone': numero, 'message': mensagem}).encode('utf-8')

    headers = {
        'Content-Type': 'application/json',
        'Accept': 'application/json',
    }
    if client_token:
        headers['Client-Token'] = client_token

    req = urllib.request.Request(url, data=payload, headers=headers, method='POST')
    with urllib.request.urlopen(req, timeout=10) as resp:
        body = resp.read()
        logger.info('Z-API: mensagem enviada para %s. Resposta: %s', numero, body[:200])
    return True


def _enviar_twilio(numero, mensagem):
    """Envia mensagem via Twilio WhatsApp API."""
    sid = _get_setting('TWILIO_ACCOUNT_SID', '')
    auth = _get_setting('TWILIO_AUTH_TOKEN', '')
    from_num = _get_setting('TWILIO_FROM_NUMBER', '')

    url = f'https://api.twilio.com/2010-04-01/Accounts/{sid}/Messages.json'
    to_num = f'whatsapp:+{numero}'

    payload = urllib.parse.urlencode({
        'From': from_num,
        'To': to_num,
        'Body': mensagem,
    }).encode('utf-8')

    credentials = b64encode(f'{sid}:{auth}'.encode()).decode()
    headers = {
        'Content-Type': 'application/x-www-form-urlencoded',
        'Authorization': f'Basic {credentials}',
    }

    req = urllib.request.Request(url, data=payload, headers=headers, method='POST')
    with urllib.request.urlopen(req, timeout=10) as resp:
        body = resp.read()
        logger.info('Twilio: mensagem enviada para %s. Resposta: %s', numero, body[:200])
    return True


def enviar_mensagem(telefone, mensagem):
    """
    Envia uma mensagem WhatsApp para o número informado.

    Parâmetros:
        telefone (str): Número no formato armazenado no banco (com ou sem DDI)
        mensagem (str): Texto da mensagem

    Retorna True em caso de sucesso, False se não configurado ou em erro.
    """
    provider = _prover_configurado()
    if not provider:
        logger.debug('WhatsApp desabilitado (WHATSAPP_PROVIDER não configurado).')
        return False

    numero = _formatar_telefone(telefone)
    if not numero:
        logger.warning('Número de telefone inválido para WhatsApp: %s', telefone)
        return False

    try:
        if provider == 'zapi':
            return _enviar_zapi(numero, mensagem)
        elif provider == 'twilio':
            return _enviar_twilio(numero, mensagem)
    except urllib.error.HTTPError as exc:
        body = exc.read()[:500] if exc.fp else b''
        logger.error(
            'Erro HTTP ao enviar WhatsApp (%s) para %s: %s — %s',
            provider, numero, exc.code, body,
        )
    except urllib.error.URLError as exc:
        logger.error('Erro de rede ao enviar WhatsApp para %s: %s', numero, exc.reason)
    except Exception as exc:
        logger.exception('Erro inesperado ao enviar WhatsApp para %s: %s', numero, exc)

    return False


# ─── Mensagens de negócio ────────────────────────────────────────────────────

def enviar_notificacao_fatura_fechada(fatura):
    """
    Notifica o cliente quando sua fatura mensal é fechada.
    
    Parâmetros:
        fatura (FaturaMensal): instância da fatura recém-fechada
    """
    cliente = fatura.cliente
    if not cliente.telefone:
        return False

    mensagem = (
        f'Olá, {cliente.nome}! 👋\n\n'
        f'Sua fatura de *{fatura.mes:02d}/{fatura.ano}* foi fechada.\n'
        f'💰 Valor total: *R$ {fatura.valor_total:.2f}*\n'
        f'📅 Vencimento: *{fatura.data_vencimento.strftime("%d/%m/%Y") if fatura.data_vencimento else "—"}*\n\n'
        f'Em caso de dúvidas, entre em contato conosco.\n'
        f'Obrigado! 🙏'
    )
    return enviar_mensagem(cliente.telefone, mensagem)


def enviar_notificacao_fatura_vencida(fatura):
    """
    Notifica o cliente quando sua fatura vence sem pagamento.

    Parâmetros:
        fatura (FaturaMensal): instância da fatura que acabou de vencer
    """
    cliente = fatura.cliente
    if not cliente.telefone:
        return False

    mensagem = (
        f'⚠️ Olá, {cliente.nome}!\n\n'
        f'Sua fatura de *{fatura.mes:02d}/{fatura.ano}* está *VENCIDA*.\n'
        f'💰 Valor em aberto: *R$ {fatura.valor_restante:.2f}*\n\n'
        f'Por favor, regularize seu pagamento o quanto antes para evitar bloqueios.\n'
        f'Obrigado! 🙏'
    )
    return enviar_mensagem(cliente.telefone, mensagem)
