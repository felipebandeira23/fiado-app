from django import forms
from .models import Pagamento, FaturaMensal


class PagamentoForm(forms.ModelForm):
    class Meta:
        model = Pagamento
        fields = ['valor', 'forma_pagamento', 'observacao']
        widgets = {
            'valor': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01', 'min': '0.01'}),
            'forma_pagamento': forms.Select(attrs={'class': 'form-select'}),
            'observacao': forms.Textarea(attrs={'class': 'form-control', 'rows': 2}),
        }


class FecharMesForm(forms.Form):
    mes = forms.IntegerField(
        min_value=1, max_value=12,
        widget=forms.Select(
            choices=[(i, f'{i:02d}') for i in range(1, 13)],
            attrs={'class': 'form-select'}
        ),
        label='Mês',
    )
    ano = forms.IntegerField(
        widget=forms.NumberInput(attrs={'class': 'form-control'}),
        label='Ano',
    )
