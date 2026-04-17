from django.test import TestCase

from .forms import ProdutoForm


class ProdutoFormTest(TestCase):
    def test_valor_zero_retorna_mensagem_clara(self):
        form = ProdutoForm(data={
            'nome': 'Café',
            'descricao': '',
            'categoria': 'Bebida',
            'valor_unitario': '0,00',
            'ativo': True,
        })

        self.assertFalse(form.is_valid())
        self.assertIn('Informe um valor maior que zero.', form.errors['valor_unitario'])

    def test_aceita_valor_com_virgula(self):
        form = ProdutoForm(data={
            'nome': 'Suco',
            'descricao': '',
            'categoria': 'Bebida',
            'valor_unitario': '10,50',
            'ativo': True,
        })

        self.assertTrue(form.is_valid(), form.errors.as_json())
