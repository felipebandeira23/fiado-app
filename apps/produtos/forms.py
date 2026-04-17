from decimal import Decimal
from django import forms
from .models import Produto


class ProdutoForm(forms.ModelForm):
    valor_unitario = forms.DecimalField(
        max_digits=10,
        decimal_places=2,
        min_value=Decimal('0.01'),
        localize=True,
        error_messages={
            'required': 'Informe o valor unitário.',
            'invalid': 'Informe um número válido (ex.: 10,50).',
            'min_value': 'Informe um valor maior que zero.',
        },
        widget=forms.TextInput(attrs={
            'inputmode': 'decimal',
            'placeholder': '0,00',
        }),
        label='Valor unitário (R$) *',
    )

    class Meta:
        model = Produto
        fields = ['nome', 'descricao', 'categoria', 'valor_unitario', 'ativo']
        widgets = {
            'nome': forms.TextInput(attrs={'autofocus': True, 'placeholder': 'Nome do produto'}),
            'descricao': forms.Textarea(attrs={'rows': 2, 'placeholder': 'Descrição (opcional)'}),
            'categoria': forms.TextInput(attrs={'placeholder': 'Ex: Bebida, Prato, Sobremesa'}),
        }
        labels = {
            'nome': 'Nome *',
            'descricao': 'Descrição',
            'categoria': 'Categoria',
            'ativo': 'Disponível para venda',
        }
