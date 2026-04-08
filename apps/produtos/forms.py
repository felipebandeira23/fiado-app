from django import forms
from .models import Produto


class ProdutoForm(forms.ModelForm):
    class Meta:
        model = Produto
        fields = ['nome', 'descricao', 'categoria', 'valor_unitario', 'ativo']
        widgets = {
            'nome': forms.TextInput(attrs={'autofocus': True, 'placeholder': 'Nome do produto'}),
            'descricao': forms.Textarea(attrs={'rows': 2, 'placeholder': 'Descrição (opcional)'}),
            'categoria': forms.TextInput(attrs={'placeholder': 'Ex: Bebida, Prato, Sobremesa'}),
            'valor_unitario': forms.NumberInput(attrs={'step': '0.01', 'min': '0', 'placeholder': '0,00'}),
        }
        labels = {
            'nome': 'Nome *',
            'descricao': 'Descrição',
            'categoria': 'Categoria',
            'valor_unitario': 'Valor unitário (R$) *',
            'ativo': 'Disponível para venda',
        }
