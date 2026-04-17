"""
Testes automatizados — App de Fiado

Cobre as regras de negócio críticas:
  - Model FaturaMensal (recalcular_pago, valor_restante, esta_quitada)
  - Model Cliente (saldo_devedor_total, gerar_codigo)
  - View fechar_mes
  - View registrar_pagamento
  - Management command verificar_vencimentos
  - API venda rápida (api_salvar_consumo)
  - Serviço WhatsApp (sem chamadas de rede)

Execução:
    python manage.py test apps.faturas.tests --verbosity=2
"""
import json
from datetime import date, timedelta
from decimal import Decimal
from io import StringIO
from unittest.mock import patch, MagicMock

from django.test import TestCase, Client as HttpClient
from django.urls import reverse
from django.core.management import call_command

from apps.clientes.models import Cliente
from apps.consumos.models import Consumo, ConsumoItem
from apps.faturas.models import FaturaMensal, Pagamento, AuditLog
from apps.faturas.management.commands.verificar_vencimentos import Command as CmdVerificar
from apps.produtos.models import Produto
from apps.usuarios.models import Usuario


# ─── Fixtures reutilizáveis ───────────────────────────────────────────────────

def _make_usuario(username='atendente', admin=False):
    """Cria e retorna um Usuario de teste."""
    usuario = Usuario.objects.create_user(
        username=username,
        password='senha123',
        perfil=Usuario.PERFIL_ADMIN if admin else Usuario.PERFIL_ATENDENTE,
    )
    return usuario


def _make_cliente(nome='João Teste', telefone='11999999999', limite=Decimal('0')):
    """Cria e retorna um Cliente de teste."""
    return Cliente.objects.create(nome=nome, telefone=telefone, limite_credito=limite)


def _make_produto(nome='Produto Teste', preco=Decimal('10.00')):
    """Cria e retorna um Produto ativo de teste."""
    return Produto.objects.create(nome=nome, valor_unitario=preco, ativo=True)


def _make_consumo(cliente, usuario, valor=Decimal('50.00'), faturado=False):
    """Cria e retorna um Consumo de teste."""
    return Consumo.objects.create(
        cliente=cliente,
        usuario=usuario,
        valor_total=valor,
        faturado=faturado,
    )


def _make_fatura(cliente, mes=None, ano=None, total=Decimal('100.00'), status=FaturaMensal.STATUS_FECHADA):
    hoje = date.today()
    return FaturaMensal.objects.create(
        cliente=cliente,
        mes=mes or hoje.month,
        ano=ano or hoje.year,
        valor_total=total,
        status=status,
        data_fechamento=hoje,
        data_vencimento=hoje + timedelta(days=30),
    )


# ─── Testes de Model: FaturaMensal ───────────────────────────────────────────

class FaturaMensalModelTest(TestCase):

    def setUp(self):
        self.usuario = _make_usuario()
        self.cliente = _make_cliente()

    def test_valor_restante_sem_pagamentos(self):
        fatura = _make_fatura(self.cliente, total=Decimal('200.00'))
        self.assertEqual(fatura.valor_restante, Decimal('200.00'))

    def test_esta_quitada_false_sem_pagamento(self):
        fatura = _make_fatura(self.cliente, total=Decimal('200.00'))
        self.assertFalse(fatura.esta_quitada)

    def test_recalcular_pago_atualiza_valor_pago(self):
        fatura = _make_fatura(self.cliente, total=Decimal('200.00'))
        Pagamento.objects.create(
            fatura=fatura,
            valor=Decimal('80.00'),
            forma_pagamento=Pagamento.FORMA_DINHEIRO,
            registrado_por=self.usuario,
        )
        fatura.recalcular_pago()
        fatura.refresh_from_db()
        self.assertEqual(fatura.valor_pago, Decimal('80.00'))
        self.assertNotEqual(fatura.status, FaturaMensal.STATUS_PAGA)

    def test_recalcular_pago_marca_como_paga_quando_quitada(self):
        fatura = _make_fatura(self.cliente, total=Decimal('100.00'))
        Pagamento.objects.create(
            fatura=fatura,
            valor=Decimal('100.00'),
            forma_pagamento=Pagamento.FORMA_PIX,
            registrado_por=self.usuario,
        )
        fatura.recalcular_pago()
        fatura.refresh_from_db()
        self.assertEqual(fatura.status, FaturaMensal.STATUS_PAGA)
        self.assertEqual(fatura.valor_restante, Decimal('0.00'))

    def test_esta_quitada_true_apos_pagamento_completo(self):
        fatura = _make_fatura(self.cliente, total=Decimal('50.00'))
        fatura.valor_pago = Decimal('50.00')
        fatura.save()
        self.assertTrue(fatura.esta_quitada)

    def test_str_retorna_representacao_legivel(self):
        fatura = _make_fatura(self.cliente, mes=3, ano=2025, total=Decimal('10.00'))
        self.assertIn('03/2025', str(fatura))
        self.assertIn(self.cliente.nome, str(fatura))

    def test_unique_together_cliente_mes_ano(self):
        from django.db import IntegrityError
        _make_fatura(self.cliente, mes=1, ano=2025, total=Decimal('10.00'))
        with self.assertRaises(IntegrityError):
            FaturaMensal.objects.create(
                cliente=self.cliente,
                mes=1,
                ano=2025,
                valor_total=Decimal('20.00'),
                status=FaturaMensal.STATUS_ABERTA,
            )


# ─── Testes de Model: Cliente ─────────────────────────────────────────────────

class ClienteModelTest(TestCase):

    def setUp(self):
        self.usuario = _make_usuario()

    def test_codigo_gerado_automaticamente(self):
        cliente = _make_cliente()
        self.assertTrue(cliente.codigo.startswith('CLI-'))

    def test_saldo_devedor_zero_sem_faturas(self):
        cliente = _make_cliente()
        self.assertEqual(cliente.saldo_devedor_total, 0)

    def test_saldo_devedor_total_soma_faturas_em_aberto(self):
        cliente = _make_cliente()
        _make_fatura(cliente, mes=1, ano=2025, total=Decimal('100.00'), status=FaturaMensal.STATUS_FECHADA)
        _make_fatura(cliente, mes=2, ano=2025, total=Decimal('50.00'), status=FaturaMensal.STATUS_FECHADA)
        self.assertEqual(cliente.saldo_devedor_total, Decimal('150.00'))

    def test_saldo_devedor_exclui_faturas_pagas(self):
        cliente = _make_cliente()
        fatura_paga = _make_fatura(cliente, mes=1, ano=2025, total=Decimal('100.00'), status=FaturaMensal.STATUS_PAGA)
        fatura_paga.valor_pago = Decimal('100.00')
        fatura_paga.save()
        _make_fatura(cliente, mes=2, ano=2025, total=Decimal('80.00'), status=FaturaMensal.STATUS_FECHADA)
        self.assertEqual(cliente.saldo_devedor_total, Decimal('80.00'))

    def test_esta_bloqueado_false_para_ativo(self):
        cliente = _make_cliente()
        self.assertFalse(cliente.esta_bloqueado)

    def test_esta_bloqueado_true_para_bloqueado(self):
        cliente = _make_cliente()
        cliente.status = Cliente.STATUS_BLOQUEADO
        cliente.save()
        self.assertTrue(cliente.esta_bloqueado)


# ─── Testes de Signal: fatura→cliente ────────────────────────────────────────

class SignalFaturaClienteTest(TestCase):

    def setUp(self):
        self.usuario = _make_usuario()
        self.cliente = _make_cliente()

    def test_cliente_vira_inadimplente_quando_fatura_vence(self):
        fatura = _make_fatura(self.cliente, total=Decimal('100.00'), status=FaturaMensal.STATUS_FECHADA)
        fatura.status = FaturaMensal.STATUS_VENCIDA
        fatura.save(update_fields=['status'])
        self.cliente.refresh_from_db()
        self.assertEqual(self.cliente.status, Cliente.STATUS_INADIMPLENTE)

    def test_cliente_volta_ativo_quando_quita_todas_dividas(self):
        self.cliente.status = Cliente.STATUS_INADIMPLENTE
        self.cliente.save()
        fatura = _make_fatura(self.cliente, total=Decimal('100.00'), status=FaturaMensal.STATUS_FECHADA)
        fatura.status = FaturaMensal.STATUS_PAGA
        fatura.save(update_fields=['status'])
        self.cliente.refresh_from_db()
        self.assertEqual(self.cliente.status, Cliente.STATUS_ATIVO)


# ─── Testes de View: fechar_mes ──────────────────────────────────────────────

class FecharMesViewTest(TestCase):

    def setUp(self):
        self.usuario = _make_usuario(admin=True)
        self.cliente = _make_cliente()
        self.http = HttpClient()
        self.http.force_login(self.usuario)

    def _url(self):
        return reverse('faturas:fechar_mes')

    @patch('apps.faturas.views.enviar_notificacao_fatura_fechada', return_value=True)
    def test_fechar_mes_cria_fatura(self, mock_wpp):
        _make_consumo(self.cliente, self.usuario, valor=Decimal('75.00'))
        hoje = date.today()
        resp = self.http.post(self._url(), {'mes': hoje.month, 'ano': hoje.year})
        self.assertRedirects(resp, reverse('faturas:lista'))
        fatura = FaturaMensal.objects.get(cliente=self.cliente, mes=hoje.month, ano=hoje.year)
        self.assertEqual(fatura.status, FaturaMensal.STATUS_ABERTA)
        self.assertEqual(fatura.valor_total, Decimal('75.00'))

    @patch('apps.faturas.views.enviar_notificacao_fatura_fechada', return_value=False)
    def test_fechar_mes_sem_consumos_redireciona_com_aviso(self, mock_wpp):
        hoje = date.today()
        resp = self.http.post(self._url(), {'mes': hoje.month, 'ano': hoje.year}, follow=True)
        self.assertContains(resp, 'Nenhum consumo')

    @patch('apps.faturas.views.enviar_notificacao_fatura_fechada', return_value=False)
    def test_fechar_mes_marca_consumos_como_faturados(self, mock_wpp):
        consumo = _make_consumo(self.cliente, self.usuario, valor=Decimal('30.00'))
        self.assertFalse(consumo.faturado)
        hoje = date.today()
        self.http.post(self._url(), {'mes': hoje.month, 'ano': hoje.year})
        consumo.refresh_from_db()
        self.assertTrue(consumo.faturado)

    @patch('apps.faturas.views.enviar_notificacao_fatura_fechada', return_value=False)
    def test_fechar_mes_registra_auditoria(self, mock_wpp):
        _make_consumo(self.cliente, self.usuario, valor=Decimal('20.00'))
        hoje = date.today()
        self.http.post(self._url(), {'mes': hoje.month, 'ano': hoje.year})
        self.assertTrue(AuditLog.objects.filter(acao='fechar_mes').exists())

    @patch('apps.faturas.views.enviar_notificacao_fatura_fechada', return_value=True)
    def test_fechar_mes_chama_whatsapp(self, mock_wpp):
        _make_consumo(self.cliente, self.usuario, valor=Decimal('55.00'))
        hoje = date.today()
        self.http.post(self._url(), {'mes': hoje.month, 'ano': hoje.year})
        mock_wpp.assert_called_once()

    def test_fechar_mes_requer_login(self):
        http = HttpClient()
        resp = http.post(self._url(), {'mes': 1, 'ano': 2025})
        self.assertEqual(resp.status_code, 302)
        self.assertIn('/login/', resp['Location'])


# ─── Testes de View: registrar_pagamento ──────────────────────────────────────

class RegistrarPagamentoViewTest(TestCase):

    def setUp(self):
        self.usuario = _make_usuario()
        self.cliente = _make_cliente()
        self.http = HttpClient()
        self.http.force_login(self.usuario)

    def _url(self, fatura_pk):
        return reverse('faturas:pagamento', kwargs={'pk': fatura_pk})

    def test_registrar_pagamento_parcial(self):
        fatura = _make_fatura(self.cliente, total=Decimal('200.00'))
        resp = self.http.post(self._url(fatura.pk), {
            'valor': '100.00',
            'forma_pagamento': Pagamento.FORMA_DINHEIRO,
            'observacao': '',
        })
        self.assertRedirects(resp, reverse('faturas:detalhe', kwargs={'pk': fatura.pk}))
        fatura.refresh_from_db()
        self.assertEqual(fatura.valor_pago, Decimal('100.00'))
        self.assertNotEqual(fatura.status, FaturaMensal.STATUS_PAGA)

    def test_registrar_pagamento_total_marca_paga(self):
        fatura = _make_fatura(self.cliente, total=Decimal('100.00'))
        self.http.post(self._url(fatura.pk), {
            'valor': '100.00',
            'forma_pagamento': Pagamento.FORMA_PIX,
            'observacao': '',
        })
        fatura.refresh_from_db()
        self.assertEqual(fatura.status, FaturaMensal.STATUS_PAGA)

    def test_pagamento_excedente_rejeitado(self):
        fatura = _make_fatura(self.cliente, total=Decimal('50.00'))
        resp = self.http.post(self._url(fatura.pk), {
            'valor': '999.00',
            'forma_pagamento': Pagamento.FORMA_DINHEIRO,
            'observacao': '',
        }, follow=True)
        fatura.refresh_from_db()
        self.assertEqual(fatura.valor_pago, Decimal('0.00'))
        self.assertContains(resp, 'excede')

    def test_pagamento_registra_auditoria(self):
        fatura = _make_fatura(self.cliente, total=Decimal('100.00'))
        self.http.post(self._url(fatura.pk), {
            'valor': '50.00',
            'forma_pagamento': Pagamento.FORMA_DINHEIRO,
            'observacao': '',
        })
        self.assertTrue(AuditLog.objects.filter(acao='pagamento').exists())

    def test_pagamento_em_fatura_ja_paga_e_rejeitado(self):
        fatura = _make_fatura(self.cliente, total=Decimal('100.00'), status=FaturaMensal.STATUS_PAGA)
        fatura.valor_pago = Decimal('100.00')
        fatura.save()
        resp = self.http.post(self._url(fatura.pk), {
            'valor': '10.00',
            'forma_pagamento': Pagamento.FORMA_DINHEIRO,
            'observacao': '',
        }, follow=True)
        # Não deve criar novo pagamento
        self.assertEqual(fatura.pagamentos.count(), 0)

    def test_pagamento_requer_login(self):
        fatura = _make_fatura(self.cliente, total=Decimal('100.00'))
        http = HttpClient()
        resp = http.post(self._url(fatura.pk), {'valor': '10.00', 'forma_pagamento': 'dinheiro'})
        self.assertEqual(resp.status_code, 302)
        self.assertIn('/login/', resp['Location'])

    def test_pagamento_sem_valor_e_rejeitado(self):
        fatura = _make_fatura(self.cliente, total=Decimal('100.00'))
        resp = self.http.post(self._url(fatura.pk), {
            'valor': '',
            'forma_pagamento': Pagamento.FORMA_DINHEIRO,
            'observacao': '',
        })
        self.assertRedirects(resp, reverse('faturas:detalhe', kwargs={'pk': fatura.pk}))
        self.assertEqual(fatura.pagamentos.count(), 0)


# ─── Testes do Management Command: verificar_vencimentos ─────────────────────

class VerificarVencimentosCommandTest(TestCase):

    def setUp(self):
        self.usuario = _make_usuario()
        self.cliente = _make_cliente()

    def _chamar_comando(self):
        stdout = StringIO()
        call_command('verificar_vencimentos', stdout=stdout)
        return stdout.getvalue()

    @patch('apps.faturas.management.commands.verificar_vencimentos.enviar_notificacao_fatura_vencida', return_value=False)
    def test_marca_faturas_vencidas(self, mock_wpp):
        ontem = date.today() - timedelta(days=1)
        fatura = FaturaMensal.objects.create(
            cliente=self.cliente,
            mes=ontem.month,
            ano=ontem.year,
            valor_total=Decimal('100.00'),
            status=FaturaMensal.STATUS_FECHADA,
            data_fechamento=ontem - timedelta(days=30),
            data_vencimento=ontem,
        )
        self._chamar_comando()
        fatura.refresh_from_db()
        self.assertEqual(fatura.status, FaturaMensal.STATUS_VENCIDA)

    @patch('apps.faturas.management.commands.verificar_vencimentos.enviar_notificacao_fatura_vencida', return_value=False)
    def test_nao_marca_faturas_com_vencimento_futuro(self, mock_wpp):
        amanha = date.today() + timedelta(days=1)
        fatura = FaturaMensal.objects.create(
            cliente=self.cliente,
            mes=amanha.month,
            ano=amanha.year,
            valor_total=Decimal('100.00'),
            status=FaturaMensal.STATUS_FECHADA,
            data_fechamento=date.today(),
            data_vencimento=amanha,
        )
        self._chamar_comando()
        fatura.refresh_from_db()
        self.assertEqual(fatura.status, FaturaMensal.STATUS_FECHADA)

    @patch('apps.faturas.management.commands.verificar_vencimentos.enviar_notificacao_fatura_vencida', return_value=True)
    def test_chama_notificacao_whatsapp(self, mock_wpp):
        ontem = date.today() - timedelta(days=1)
        FaturaMensal.objects.create(
            cliente=self.cliente,
            mes=ontem.month,
            ano=ontem.year,
            valor_total=Decimal('100.00'),
            status=FaturaMensal.STATUS_FECHADA,
            data_fechamento=ontem - timedelta(days=30),
            data_vencimento=ontem,
        )
        output = self._chamar_comando()
        mock_wpp.assert_called_once()
        self.assertIn('enviada', output)

    @patch('apps.faturas.management.commands.verificar_vencimentos.enviar_notificacao_fatura_vencida', return_value=False)
    def test_sem_faturas_vencidas_exibe_mensagem_sucesso(self, mock_wpp):
        output = self._chamar_comando()
        self.assertIn('Nenhuma', output)

    @patch('apps.faturas.management.commands.verificar_vencimentos.enviar_notificacao_fatura_vencida', return_value=False)
    def test_cliente_vira_inadimplente_apos_vencimento(self, mock_wpp):
        ontem = date.today() - timedelta(days=1)
        FaturaMensal.objects.create(
            cliente=self.cliente,
            mes=ontem.month,
            ano=ontem.year,
            valor_total=Decimal('100.00'),
            status=FaturaMensal.STATUS_FECHADA,
            data_fechamento=ontem - timedelta(days=30),
            data_vencimento=ontem,
        )
        self._chamar_comando()
        self.cliente.refresh_from_db()
        self.assertEqual(self.cliente.status, Cliente.STATUS_INADIMPLENTE)


# ─── Testes da API: api_salvar_consumo ───────────────────────────────────────

class ApiSalvarConsumoTest(TestCase):

    def setUp(self):
        self.usuario = _make_usuario()
        self.cliente = _make_cliente()
        self.produto = _make_produto(preco=Decimal('15.00'))
        self.http = HttpClient()
        self.http.force_login(self.usuario)

    def _url(self):
        return reverse('consumos:api_salvar')

    def _post(self, payload):
        return self.http.post(
            self._url(),
            data=json.dumps(payload),
            content_type='application/json',
        )

    def test_salvar_consumo_simples(self):
        resp = self._post({
            'cliente_id': str(self.cliente.pk),
            'itens': [{'produto_id': str(self.produto.pk), 'quantidade': 2}],
        })
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertTrue(data['sucesso'])
        self.assertEqual(data['valor_total'], 30.0)
        self.assertEqual(Consumo.objects.count(), 1)
        consumo = Consumo.objects.first()
        self.assertEqual(consumo.valor_total, Decimal('30.00'))
        self.assertEqual(consumo.itens.count(), 1)

    def test_salvar_consumo_multiplos_itens(self):
        produto2 = _make_produto(nome='Produto 2', preco=Decimal('5.00'))
        resp = self._post({
            'cliente_id': str(self.cliente.pk),
            'itens': [
                {'produto_id': str(self.produto.pk), 'quantidade': 1},
                {'produto_id': str(produto2.pk), 'quantidade': 3},
            ],
        })
        data = resp.json()
        self.assertTrue(data['sucesso'])
        self.assertAlmostEqual(data['valor_total'], 30.0)  # 15 + 3*5

    def test_cliente_nao_encontrado_retorna_404(self):
        import uuid
        resp = self._post({
            'cliente_id': str(uuid.uuid4()),
            'itens': [{'produto_id': str(self.produto.pk), 'quantidade': 1}],
        })
        self.assertEqual(resp.status_code, 404)

    def test_sem_itens_retorna_400(self):
        resp = self._post({'cliente_id': str(self.cliente.pk), 'itens': []})
        self.assertEqual(resp.status_code, 400)
        self.assertIn('erro', resp.json())

    def test_sem_cliente_retorna_400(self):
        resp = self._post({'itens': [{'produto_id': str(self.produto.pk), 'quantidade': 1}]})
        self.assertEqual(resp.status_code, 400)

    def test_cliente_bloqueado_retorna_403(self):
        self.cliente.status = Cliente.STATUS_BLOQUEADO
        self.cliente.save()
        resp = self._post({
            'cliente_id': str(self.cliente.pk),
            'itens': [{'produto_id': str(self.produto.pk), 'quantidade': 1}],
        })
        self.assertEqual(resp.status_code, 403)

    def test_produto_inativo_retorna_400(self):
        self.produto.ativo = False
        self.produto.save()
        resp = self._post({
            'cliente_id': str(self.cliente.pk),
            'itens': [{'produto_id': str(self.produto.pk), 'quantidade': 1}],
        })
        self.assertEqual(resp.status_code, 400)

    def test_json_invalido_retorna_400(self):
        resp = self.http.post(self._url(), data='not-json', content_type='application/json')
        self.assertEqual(resp.status_code, 400)

    def test_aviso_limite_credito_nao_bloqueia(self):
        """Consumo acima do limite gera aviso mas não bloqueia."""
        self.cliente.limite_credito = Decimal('10.00')
        self.cliente.save()
        resp = self._post({
            'cliente_id': str(self.cliente.pk),
            'itens': [{'produto_id': str(self.produto.pk), 'quantidade': 2}],  # R$ 30 > limite R$ 10
        })
        data = resp.json()
        self.assertTrue(data['sucesso'])
        self.assertIn('aviso', data)

    def test_api_requer_autenticacao(self):
        http = HttpClient()
        resp = http.post(self._url(), data='{}', content_type='application/json')
        self.assertEqual(resp.status_code, 302)

    def test_salvar_consumo_atualiza_saldo_devedor_do_cliente(self):
        self._post({
            'cliente_id': str(self.cliente.pk),
            'itens': [{'produto_id': str(self.produto.pk), 'quantidade': 2}],
        })
        self.cliente.refresh_from_db()
        self.assertEqual(self.cliente.saldo_devedor_total, Decimal('30.00'))


class ListaFaturasViewTest(TestCase):

    def setUp(self):
        self.usuario = _make_usuario()
        self.cliente = _make_cliente()
        self.http = HttpClient()
        self.http.force_login(self.usuario)

    def test_lista_faturas_aplica_ano_atual_por_padrao(self):
        hoje = date.today()
        _make_fatura(self.cliente, mes=hoje.month, ano=hoje.year, total=Decimal('50.00'))
        _make_fatura(self.cliente, mes=1, ano=hoje.year - 1, total=Decimal('25.00'))

        resp = self.http.get(reverse('faturas:lista'))
        self.assertEqual(resp.context['ano_filtro'], str(hoje.year))
        self.assertEqual(resp.context['faturas'].paginator.count, 1)


# ─── Testes do Serviço: WhatsApp ──────────────────────────────────────────────

class WhatsAppServiceTest(TestCase):

    def test_sem_provedor_configurado_retorna_false(self):
        from apps.faturas.whatsapp import enviar_mensagem
        with self.settings(WHATSAPP_PROVIDER=''):
            result = enviar_mensagem('11999999999', 'teste')
            self.assertFalse(result)

    def test_formatar_telefone_adiciona_ddi_55(self):
        from apps.faturas.whatsapp import _formatar_telefone
        self.assertEqual(_formatar_telefone('11999999999'), '5511999999999')

    def test_formatar_telefone_nao_duplica_ddi(self):
        from apps.faturas.whatsapp import _formatar_telefone
        self.assertEqual(_formatar_telefone('5511999999999'), '5511999999999')

    def test_formatar_telefone_remove_simbolos(self):
        from apps.faturas.whatsapp import _formatar_telefone
        self.assertEqual(_formatar_telefone('(11) 9 9999-9999'), '5511999999999')

    def test_formatar_telefone_vazio_retorna_vazio(self):
        from apps.faturas.whatsapp import _formatar_telefone
        self.assertEqual(_formatar_telefone(''), '')

    @patch('apps.faturas.whatsapp._enviar_zapi')
    def test_zapi_chamado_quando_configurado(self, mock_zapi):
        from apps.faturas.whatsapp import enviar_mensagem
        mock_zapi.return_value = True
        with self.settings(
            WHATSAPP_PROVIDER='zapi',
            ZAPI_INSTANCE_ID='abc123',
            ZAPI_TOKEN='tok456',
        ):
            result = enviar_mensagem('11999999999', 'olá')
        mock_zapi.assert_called_once()
        self.assertTrue(result)

    @patch('apps.faturas.whatsapp._enviar_twilio')
    def test_twilio_chamado_quando_configurado(self, mock_twilio):
        from apps.faturas.whatsapp import enviar_mensagem
        mock_twilio.return_value = True
        with self.settings(
            WHATSAPP_PROVIDER='twilio',
            TWILIO_ACCOUNT_SID='sid',
            TWILIO_AUTH_TOKEN='auth',
            TWILIO_FROM_NUMBER='whatsapp:+5511999999999',
        ):
            result = enviar_mensagem('11888888888', 'olá')
        mock_twilio.assert_called_once()
        self.assertTrue(result)

    @patch('apps.faturas.whatsapp._enviar_zapi', side_effect=Exception('rede fora'))
    def test_erro_de_rede_retorna_false_sem_exception(self, mock_zapi):
        from apps.faturas.whatsapp import enviar_mensagem
        with self.settings(
            WHATSAPP_PROVIDER='zapi',
            ZAPI_INSTANCE_ID='abc',
            ZAPI_TOKEN='tok',
        ):
            result = enviar_mensagem('11999999999', 'olá')
        self.assertFalse(result)

    def test_notificacao_fatura_fechada_sem_telefone_retorna_false(self):
        from apps.faturas.whatsapp import enviar_notificacao_fatura_fechada
        usuario = _make_usuario(username='u_wpp')
        cliente = Cliente.objects.create(nome='Sem Tel', telefone='')
        fatura = _make_fatura(cliente)
        result = enviar_notificacao_fatura_fechada(fatura)
        self.assertFalse(result)

    def test_notificacao_fatura_vencida_sem_telefone_retorna_false(self):
        from apps.faturas.whatsapp import enviar_notificacao_fatura_vencida
        cliente = Cliente.objects.create(nome='Sem Tel 2', telefone='')
        fatura = _make_fatura(cliente)
        result = enviar_notificacao_fatura_vencida(fatura)
        self.assertFalse(result)
