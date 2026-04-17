import json
from decimal import Decimal

from django.test import TestCase, Client as HttpClient

from apps.clientes.models import Cliente
from apps.consumos.models import Consumo, ConsumoItem
from apps.consumos.views import PRODUTO_ITEM_AVULSO_NOME
from apps.produtos.models import Produto
from apps.usuarios.models import Usuario


class ApiSalvarConsumoAvulsoTest(TestCase):
    def setUp(self):
        self.http = HttpClient()
        self.usuario = Usuario.objects.create_user(
            username='atendente-avulso',
            password='senha123',
            perfil=Usuario.PERFIL_ATENDENTE,
        )
        self.cliente = Cliente.objects.create(nome='Cliente Avulso', telefone='11999990000')
        self.http.force_login(self.usuario)

    def post_json(self, payload):
        return self.http.post(
            '/api/consumos/salvar/',
            data=json.dumps(payload),
            content_type='application/json',
        )

    def test_salva_item_avulso_sem_produto_id(self):
        response = self.post_json({
            'cliente_id': str(self.cliente.id),
            'observacao': 'teste avulso',
            'itens': [
                {'avulso': True, 'valor_unitario': 12.50, 'quantidade': 1},
            ],
        })

        self.assertEqual(response.status_code, 200, response.content)
        self.assertEqual(Consumo.objects.count(), 1)
        self.assertEqual(ConsumoItem.objects.count(), 1)

        item = ConsumoItem.objects.select_related('produto').first()
        self.assertEqual(item.produto.nome, PRODUTO_ITEM_AVULSO_NOME)
        self.assertEqual(item.valor_unitario, Decimal('12.50'))
        self.assertEqual(item.subtotal, Decimal('12.50'))
        self.assertFalse(item.produto.ativo)

    def test_rejeita_item_avulso_com_valor_invalido(self):
        response = self.post_json({
            'cliente_id': str(self.cliente.id),
            'itens': [
                {'avulso': True, 'valor_unitario': 0, 'quantidade': 1},
            ],
        })

        self.assertEqual(response.status_code, 400)
        self.assertIn('Valor avulso', response.json()['erro'])
        self.assertEqual(Consumo.objects.count(), 0)

    def test_produto_normal_continua_usando_preco_do_cadastro(self):
        produto = Produto.objects.create(
            nome='Refrigerante',
            categoria='Bebida',
            valor_unitario=Decimal('7.90'),
            ativo=True,
        )

        response = self.post_json({
            'cliente_id': str(self.cliente.id),
            'itens': [
                {
                    'produto_id': str(produto.id),
                    'quantidade': 2,
                    'valor_unitario': 1.00,
                },
            ],
        })

        self.assertEqual(response.status_code, 200, response.content)
        item = ConsumoItem.objects.select_related('produto').first()
        self.assertEqual(item.produto_id, produto.id)
        self.assertEqual(item.valor_unitario, Decimal('7.90'))
        self.assertEqual(item.subtotal, Decimal('15.80'))
