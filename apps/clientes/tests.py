from datetime import date
from decimal import Decimal

from django.test import TestCase
from django.urls import reverse

from apps.clientes.forms import ClienteForm
from apps.clientes.models import Cliente
from apps.consumos.models import Consumo
from apps.faturas.models import FaturaMensal
from apps.usuarios.models import Usuario


class ClienteFormTest(TestCase):

    def test_clean_cpf_aceita_valor_ausente_sem_quebrar(self):
        form = ClienteForm(data={
            'nome': 'João',
            'telefone': '11999999999',
            'cpf': None,
            'limite_credito': '0',
            'status': 'ativo',
        })
        self.assertTrue(form.is_valid())
        self.assertIsNone(form.cleaned_data['cpf'])

    def test_nome_minimo_deve_ter_2_caracteres(self):
        form = ClienteForm(data={
            'nome': 'A',
            'telefone': '11999999999',
            'cpf': '',
            'limite_credito': '0',
            'status': 'ativo',
        })
        self.assertFalse(form.is_valid())
        self.assertIn('nome', form.errors)


class ClientePerfilSelfServiceTest(TestCase):

    def setUp(self):
        self.atendente = Usuario.objects.create_user(
            username='atendente',
            password='senha123',
            perfil=Usuario.PERFIL_ATENDENTE,
        )
        self.usuario_cliente = Usuario.objects.create_user(
            username='cliente-user',
            password='senha123',
            perfil=Usuario.PERFIL_ATENDENTE,
        )

        self.cliente_logado = Cliente.objects.create(
            nome='Cliente Logado',
            telefone='11999990000',
            usuario=self.usuario_cliente,
        )
        self.outro_cliente = Cliente.objects.create(
            nome='Outro Cliente',
            telefone='11888887777',
        )

        self.consumo_cliente_logado = Consumo.objects.create(
            cliente=self.cliente_logado,
            usuario=self.atendente,
            valor_total=Decimal('35.00'),
        )
        self.consumo_outro = Consumo.objects.create(
            cliente=self.outro_cliente,
            usuario=self.atendente,
            valor_total=Decimal('90.00'),
        )

        self.fatura_cliente_logado = FaturaMensal.objects.create(
            cliente=self.cliente_logado,
            mes=date.today().month,
            ano=date.today().year,
            valor_total=Decimal('120.00'),
            valor_pago=Decimal('20.00'),
            status=FaturaMensal.STATUS_FECHADA,
        )
        self.fatura_outro = FaturaMensal.objects.create(
            cliente=self.outro_cliente,
            mes=1,
            ano=date.today().year - 1,
            valor_total=Decimal('80.00'),
            status=FaturaMensal.STATUS_FECHADA,
        )

    def test_dashboard_redireciona_cliente_para_meu_perfil(self):
        self.client.force_login(self.usuario_cliente)
        response = self.client.get(reverse('clientes:dashboard'))
        self.assertRedirects(response, reverse('clientes:meu_perfil'))

    def test_meu_perfil_mostra_apenas_dados_do_cliente_logado(self):
        self.client.force_login(self.usuario_cliente)
        response = self.client.get(reverse('clientes:meu_perfil'))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Cliente Logado')
        self.assertNotContains(response, 'Outro Cliente')

    def test_cliente_nao_acessa_detalhe_de_outro_cliente(self):
        self.client.force_login(self.usuario_cliente)
        response = self.client.get(reverse('clientes:detalhe', kwargs={'pk': self.outro_cliente.pk}))
        self.assertEqual(response.status_code, 404)

    def test_cliente_lista_apenas_proprios_consumos(self):
        self.client.force_login(self.usuario_cliente)
        response = self.client.get(reverse('consumos:lista'))

        self.assertContains(response, reverse('consumos:detalhe', kwargs={'pk': self.consumo_cliente_logado.pk}))
        self.assertNotContains(response, reverse('consumos:detalhe', kwargs={'pk': self.consumo_outro.pk}))

    def test_cliente_nao_acessa_detalhe_consumo_de_outro_cliente(self):
        self.client.force_login(self.usuario_cliente)
        response = self.client.get(reverse('consumos:detalhe', kwargs={'pk': self.consumo_outro.pk}))
        self.assertRedirects(response, reverse('clientes:meu_perfil'))

    def test_cliente_lista_apenas_proprias_faturas(self):
        self.client.force_login(self.usuario_cliente)
        response = self.client.get(reverse('faturas:lista'))

        self.assertContains(response, f'{self.fatura_cliente_logado.mes:02d}/{self.fatura_cliente_logado.ano}')
        self.assertNotContains(response, f'{self.fatura_outro.mes:02d}/{self.fatura_outro.ano}')

    def test_cliente_nao_acessa_fatura_de_outro_cliente(self):
        self.client.force_login(self.usuario_cliente)
        response = self.client.get(reverse('faturas:detalhe', kwargs={'pk': self.fatura_outro.pk}))
        self.assertRedirects(response, reverse('clientes:meu_perfil'))

    def test_api_debito_bloqueia_consulta_de_outro_cliente(self):
        self.client.force_login(self.usuario_cliente)
        response = self.client.get(reverse('faturas:api_debito', kwargs={'cliente_id': self.outro_cliente.pk}))
        self.assertEqual(response.status_code, 403)

    def test_fluxo_interno_permanece_para_atendente(self):
        self.client.force_login(self.atendente)
        response = self.client.get(reverse('clientes:detalhe', kwargs={'pk': self.outro_cliente.pk}))
        self.assertEqual(response.status_code, 200)
