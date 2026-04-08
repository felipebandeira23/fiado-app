from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse
from django.shortcuts import render, redirect, get_object_or_404
from django.views.decorators.http import require_GET, require_POST
from .models import Produto
from .forms import ProdutoForm


@login_required
def lista_produtos(request):
    categoria = request.GET.get('categoria', '')
    qs = Produto.objects.all()
    if categoria:
        qs = qs.filter(categoria__icontains=categoria)

    categorias = Produto.objects.values_list('categoria', flat=True).distinct().exclude(categoria='')
    return render(request, 'produtos/lista.html', {
        'produtos': qs,
        'categorias': categorias,
        'categoria_filtro': categoria,
    })


@login_required
def novo_produto(request):
    if not request.user.is_admin_sistema:
        messages.error(request, 'Apenas administradores podem cadastrar produtos.')
        return redirect('produtos:lista')

    if request.method == 'POST':
        form = ProdutoForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, 'Produto cadastrado com sucesso!')
            return redirect('produtos:lista')
    else:
        form = ProdutoForm()
    return render(request, 'produtos/form.html', {'form': form, 'titulo': 'Novo Produto'})


@login_required
def editar_produto(request, pk):
    if not request.user.is_admin_sistema:
        messages.error(request, 'Apenas administradores podem editar produtos.')
        return redirect('produtos:lista')

    produto = get_object_or_404(Produto, pk=pk)
    if request.method == 'POST':
        form = ProdutoForm(request.POST, instance=produto)
        if form.is_valid():
            form.save()
            messages.success(request, 'Produto atualizado!')
            return redirect('produtos:lista')
    else:
        form = ProdutoForm(instance=produto)
    return render(request, 'produtos/form.html', {
        'form': form,
        'titulo': 'Editar Produto',
        'produto': produto,
    })


@login_required
@require_POST
def toggle_ativo(request, pk):
    """Liga/desliga disponibilidade do produto (chamado via AJAX ou botão)."""
    if not request.user.is_admin_sistema:
        return JsonResponse({'erro': 'Sem permissão.'}, status=403)
    produto = get_object_or_404(Produto, pk=pk)
    produto.ativo = not produto.ativo
    produto.save(update_fields=['ativo'])
    return JsonResponse({'ativo': produto.ativo})


@login_required
@require_GET
def api_produtos_ativos(request):
    """Retorna lista de produtos ativos em JSON (para Venda Rápida)."""
    produtos = Produto.objects.filter(ativo=True).values(
        'id', 'nome', 'categoria', 'valor_unitario'
    )
    data = [
        {
            'id': str(p['id']),
            'nome': p['nome'],
            'categoria': p['categoria'],
            'valor_unitario': float(p['valor_unitario']),
        }
        for p in produtos
    ]
    return JsonResponse(data, safe=False)
