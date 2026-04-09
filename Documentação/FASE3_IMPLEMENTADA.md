# Relatório — Implementação da Fase 3

**Data:** 09/04/2026  
**Status:** ✅ Completa e migrada no banco (Supabase)

---

## O que foi implementado

### 1. Novo App: `apps/faturas`

Criado do zero com a seguinte estrutura:

```
apps/faturas/
├── __init__.py
├── apps.py
├── admin.py
├── forms.py
├── models.py
├── urls.py
├── views.py
└── migrations/
    ├── __init__.py
    └── 0001_initial.py
```

---

### 2. Models (`apps/faturas/models.py`)

#### `FaturaMensal`
Fatura mensal de um cliente. Campos principais:
- `cliente` → FK para `clientes.Cliente`
- `mes`, `ano` → período da fatura
- `valor_total`, `valor_pago` → controle financeiro
- `status` → `aberta | fechada | paga | vencida`
- `data_fechamento`, `data_vencimento`
- Constraint `unique_together`: `(cliente, mes, ano)` — impede duplicatas
- Métodos: `recalcular_total()`, `recalcular_pago()`, `valor_restante` (property), `esta_quitada` (property)

#### `Pagamento`
Registro de cada pagamento recebido. Campos:
- `fatura` → FK para `FaturaMensal`
- `valor`, `forma_pagamento` → `dinheiro | pix | cartao_debito | cartao_credito`
- `data`, `registrado_por`, `observacao`

---

### 3. Model atualizado: `apps/consumos/models.py`

Adicionado o campo que estava pendente desde a Fase 2:
```python
fatura = models.ForeignKey('faturas.FaturaMensal', on_delete=SET_NULL, null=True, blank=True)
```
Migration gerada: `consumos/migrations/0002_consumo_fatura.py`

---

### 4. Views (`apps/faturas/views.py`)

| View | URL | Descrição |
|------|-----|-----------|
| `lista_faturas` | `GET /faturas/` | Lista todas as faturas com filtros |
| `detalhe_fatura` | `GET /faturas/<uuid>/` | Detalhe + histórico de pagamentos |
| `registrar_pagamento` | `POST /faturas/<uuid>/pagamento/` | Registra um pagamento |
| `fechar_mes` | `GET/POST /faturas/fechar-mes/` | Gera faturas do mês a partir dos consumos |
| `api_debito_cliente` | `GET /api/cliente/<uuid>/debito/` | API JSON com saldo devedor |

---

### 5. Templates criados

- `templates/faturas/lista.html` — cards de resumo, filtros, tabela de faturas
- `templates/faturas/detalhe.html` — consumos da fatura, form de pagamento, histórico
- `templates/faturas/fechar_mes.html` — formulário para fechar mês

---

### 6. Arquivos atualizados

| Arquivo | Mudança |
|---------|---------|
| `fiado_project/settings.py` | Adicionado `apps.faturas` em `INSTALLED_APPS` |
| `fiado_project/urls.py` | Incluído `apps.faturas.urls` |
| `templates/base.html` | Sidebar: links de Faturas e Fechar Mês ativados |
| `templates/dashboard.html` | Novo card "A receber", card "Faturas vencidas", tabela de últimas faturas, ações rápidas atualizadas |
| `apps/clientes/models.py` | `saldo_devedor_total` implementado consultando `FaturaMensal` |
| `apps/clientes/views.py` | Dashboard agora passa `total_a_receber`, `faturas_vencidas`, `ultimas_faturas` |

---

### 7. Migrations

```
apps\faturas\migrations\0001_initial.py        → criado
apps\consumos\migrations\0002_consumo_fatura.py → criado
```

Todas as migrations foram aplicadas com sucesso no banco Supabase:
```
Applying faturas.0001_initial... OK
Applying consumos.0002_consumo_fatura... OK
```

---

## Fluxo de uso

1. **Registrar consumos** → Venda Rápida (já existia)
2. **Fechar o mês** → `Faturas > Fechar Mês` → selecionar mês/ano → Gerar Faturas
   - Agrupa todos os consumos não faturados por cliente
   - Cria/atualiza `FaturaMensal` com status `fechada`
   - Vincula os consumos à fatura e marca como `faturado=True`
3. **Receber pagamento** → `Faturas > [selecionar fatura] > Registrar Pagamento`
   - Suporta pagamentos parciais
   - Atualiza `valor_pago` e muda status para `paga` quando quitada
4. **Dashboard** → exibe total a receber e faturas vencidas em tempo real

---

## Próximos passos (Fase 4)

- Relatórios financeiros (receita por período, inadimplência)
- Auditoria de ações críticas
- Marcar clientes como `inadimplente` automaticamente quando fatura vencer
- Envio de cobrança por WhatsApp
