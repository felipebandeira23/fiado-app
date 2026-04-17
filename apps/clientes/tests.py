from django.test import SimpleTestCase

from .forms import ClienteForm


class ClienteFormTest(SimpleTestCase):
    def test_clean_cpf_aceita_vazio_sem_quebrar(self):
        form = ClienteForm(data={
            'nome': 'Cliente Teste',
            'telefone': '11999999999',
            'cpf': '',
            'limite_credito': '0',
            'status': 'ativo',
        })
        self.assertTrue(form.is_valid())
        self.assertIsNone(form.cleaned_data['cpf'])

    def test_nome_com_menos_de_tres_caracteres_invalido(self):
        form = ClienteForm(data={
            'nome': 'aa',
            'telefone': '11999999999',
            'limite_credito': '0',
            'status': 'ativo',
        })
        self.assertFalse(form.is_valid())
        self.assertIn('nome', form.errors)
