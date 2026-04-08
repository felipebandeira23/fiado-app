from django import forms
from .models import Cliente


class ClienteForm(forms.ModelForm):
    class Meta:
        model = Cliente
        fields = [
            'nome', 'telefone', 'cpf', 'endereco',
            'foto', 'limite_credito', 'status', 'observacoes',
        ]
        widgets = {
            'nome': forms.TextInput(attrs={'autofocus': True, 'placeholder': 'Nome completo do cliente'}),
            'telefone': forms.TextInput(attrs={'placeholder': '(99) 99999-9999'}),
            'cpf': forms.TextInput(attrs={'placeholder': '000.000.000-00'}),
            'endereco': forms.Textarea(attrs={'rows': 2, 'placeholder': 'Endereço completo (opcional)'}),
            'observacoes': forms.Textarea(attrs={'rows': 2, 'placeholder': 'Notas internas sobre o cliente'}),
            'limite_credito': forms.NumberInput(attrs={'step': '0.01', 'min': '0'}),
        }
        labels = {
            'nome': 'Nome completo *',
            'telefone': 'Telefone / WhatsApp *',
            'cpf': 'CPF',
            'endereco': 'Endereço',
            'foto': 'Foto do cliente',
            'limite_credito': 'Limite de crédito (R$)',
            'status': 'Status',
            'observacoes': 'Observações',
        }

    def clean_cpf(self):
        cpf = self.cleaned_data.get('cpf', '').strip()
        if not cpf:
            return None
        return cpf
