# Relatório — Implementação da Fase 4

**Data:** 09/04/2026
**Status:** ✅ Completa — `python manage.py check` passou sem erros, sem novas migrations necessárias.

---

## O que foi implementado

### 1. Correção de bugs (queries com `valor_restante`)

`valor_restante` é uma `@property` do model — não pode ser usada em `.aggregate()` direto.
Substituído por `ExpressionWrapper(F('valor_total') - F('valor_pago'))` em:

- `apps/faturas/views.py` → `lista_faturas()`
- `apps/clientes/views.py` → `dashboard()`

Antes carregava todos os objetos em memória com `sum(f.valor_restante for f in qs)`.
Agora faz um único `SUM` no banco via SQL.

---

### 2. Signals automáticos (`apps/faturas/signals.py`)

Dois signals `post_save` registrados via `FaturasConfig.ready()`:

| Signal | Trigger | Ação |
|--------|---------|------|
| `atualizar_status_cliente_fatura` | `FaturaMensal` salva | Se `status=VENCIDA` → cliente vira **INADIMPLENTE**; se `status=PAGA` e sem outras dívidas → cliente volta para **ATIVO** |
| `recalcular_fatura_apos_pagamento` | `Pagamento` criado | Chama `fatura.recalcular_pago()` automaticamente |

A view `registrar_pagamento` foi simplificada — não chama mais `recalcular_pago()` manualmente (o signal cuida disso).

---

### 3. Management command `verificar_vencimentos`

```
apps/faturas/management/commands/verificar_vencimentos.py
```

**Uso:**
```bash
python manage.py verificar_vencimentos
```

Marca como `VENCIDA` toda `FaturaMensal` com `status=FECHADA` e `data_vencimento < hoje`.
O signal cuida de atualizar o cliente para `INADIMPLENTE` em seguida.

**Para automatizar (cron no Railway ou servidor):**
```
0 6 * * * python manage.py verificar_vencimentos
```

---

### 4. Página de Relatórios (`/relatorios/`)

Nova view `relatorios()` em `apps/faturas/views.py`. Template: `templates/relatorios/relatorios.html`.

**Seções da página:**

| Seção | Descrição |
|-------|-----------|
| Cards de resumo | Total faturado histórico, total recebido, total em aberto |
| Receita por mês | Últimos 12 meses: faturado vs recebido com barra de progresso de eficiência |
| Top 10 clientes | Ranking por consumo total, com troféus para os 3 primeiros |
| Clientes com débito | Inadimplentes e bloqueados com saldo devedor, ordenados por valor |
| Faturas vencidas | Lista de faturas em atraso com link direto para receber pagamento |

Todas as queries usam agregação no banco (sem carregar objetos em memória).

---

### 5. Ficha do cliente atualizada (`templates/clientes/detalhe.html`)

- **Saldo devedor** agora verde quando R$ 0,00 e vermelho quando positivo
- **Novos botões** no card financeiro:
  - "Ver faturas" → filtra a lista de faturas pelo nome do cliente
  - "Bloquear / Desbloquear cliente" → visível apenas para administradores, com confirmação
- **Tabela de faturas do cliente** adicionada no rodapé da página (últimas 12 faturas)

View `detalhe_cliente` atualizada para passar `faturas` no contexto.

---

### 6. Ação de bloqueio/desbloqueio de cliente

Nova view `alternar_bloqueio_cliente()` em `apps/faturas/views.py`:
- URL: `POST /clientes/<uuid>/bloquear/`
- Restrita a `is_admin_sistema`
- Alterna entre `ATIVO ↔ BLOQUEADO` com mensagem de confirmação no browser

---

### 7. Sidebar — Relatórios habilitado

Link "Relatórios" na sidebar deixou de ser `disabled` e agora aponta para `/relatorios/`.
Destaca como `active` quando a página está ativa.

---

## Resumo de arquivos modificados

| Arquivo | Tipo | Mudança |
|---------|------|---------|
| `apps/faturas/signals.py` | Novo | Signals de status automático |
| `apps/faturas/apps.py` | Editado | `ready()` registra signals |
| `apps/faturas/views.py` | Editado | Correção de queries + view `relatorios` + view `alternar_bloqueio_cliente` |
| `apps/faturas/urls.py` | Editado | Rotas `/relatorios/` e `/clientes/<uuid>/bloquear/` |
| `apps/faturas/management/commands/verificar_vencimentos.py` | Novo | Command diário |
| `apps/clientes/views.py` | Editado | Correção de query no dashboard + faturas no `detalhe_cliente` |
| `templates/relatorios/relatorios.html` | Novo | Página de relatórios completa |
| `templates/clientes/detalhe.html` | Editado | Botões de ação + tabela de faturas |
| `templates/base.html` | Editado | Link Relatórios ativo no sidebar |

---

## Estado atual do projeto

| Fase | Status |
|------|--------|
| Fase 1 — Auth, Clientes, Produtos, QR Code | ✅ Completa |
| Fase 2 — Venda Rápida, Leitura QR | ✅ Completa |
| Fase 3 — Faturas Mensais, Pagamentos | ✅ Completa |
| Fase 4 — Relatórios, Auditoria, Inadimplência auto | ✅ Completa |

---

## Próximos passos sugeridos

- **Agendamento automático** do `verificar_vencimentos` no Railway (cron job)
- **Notificação por WhatsApp** ao fechar fatura (via API da Twilio ou Z-API)
- **Exportar relatório** em PDF ou Excel (usando `reportlab` já instalado)
- **Auditoria de ações** — log de quem bloqueou, pagou, fechou mês
