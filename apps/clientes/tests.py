from django.test import TestCase

from apps.clientes.forms import ClienteForm


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
