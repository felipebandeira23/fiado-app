# Storage em Produção — Supabase Storage (S3)

**Data:** 09/04/2026
**Status:** ✅ Implementado — `python manage.py check` passou sem erros.

---

## Problema resolvido

O Railway usa **filesystem efêmero**: a cada novo deploy, qualquer arquivo salvo em disco
(fotos de clientes, QR codes) é apagado. Isso tornava o sistema inutilizável em produção.

**Solução:** usar o **Supabase Storage**, que já faz parte do projeto e é compatível com a
API S3 da AWS. Os arquivos ficam persistidos na nuvem independente de deploys.

---

## Arquivos modificados

| Arquivo | Mudança |
|---------|---------|
| `requirements.txt` | Adicionado `django-storages[s3]==1.14.6` e `boto3==1.42.86` |
| `fiado_project/settings.py` | Storage condicional: local em dev, S3 em produção |
| `fiado_project/storage_backends.py` | Novo — classe `SupabaseMediaStorage` |
| `.env.example` | Adicionadas variáveis `SUPABASE_S3_*` |

---

## Como o storage funciona

```
SUPABASE_S3_KEY_ID definida?
  ├── SIM → SupabaseMediaStorage (S3) — para Railway/produção
  └── NÃO → FileSystemStorage local — para desenvolvimento
```

Em desenvolvimento o `.env` local NÃO precisa ter as variáveis S3 — continua
salvando em `media/` como antes.

---

## Passos para ativar em produção

### 1. Criar o bucket no Supabase

1. Acesse o [Supabase Dashboard](https://supabase.com/dashboard)
2. Selecione o projeto `omotrnozchenzuobhgen`
3. Vá em **Storage → New Bucket**
4. Nome: `media`
5. Marque **"Public bucket"** ← obrigatório para URLs públicas funcionarem
6. Clique em **Create bucket**

### 2. Criar as S3 Access Keys

1. No Supabase, vá em **Storage → S3 Access Keys**
2. Clique em **New access key**
3. Copie o **Access Key ID** e o **Secret Access Key** (o secret só aparece uma vez!)

### 3. Configurar variáveis no Railway

No [Railway Dashboard](https://railway.app) → seu projeto → **Variables**, adicione:

```
SUPABASE_S3_KEY_ID      = <Access Key ID copiado>
SUPABASE_S3_SECRET      = <Secret Access Key copiado>
SUPABASE_S3_BUCKET      = media
SUPABASE_S3_ENDPOINT    = https://omotrnozchenzuobhgen.supabase.co/storage/v1/s3
SUPABASE_S3_PUBLIC_DOMAIN = omotrnozchenzuobhgen.supabase.co/storage/v1/object/public/media
```

> O Project Reference ID do seu projeto Supabase é: `omotrnozchenzuobhgen`

### 4. Deploy

Após adicionar as variáveis, o Railway fará o redeploy automático.
A partir daí, toda foto de cliente e QR code gerado será armazenado no Supabase Storage.

---

## Como funciona a URL dos arquivos

| Ambiente | Exemplo de URL |
|----------|---------------|
| Desenvolvimento | `http://localhost:8000/media/clientes/fotos/abc.jpg` |
| Produção | `https://omotrnozchenzuobhgen.supabase.co/storage/v1/object/public/media/clientes/fotos/abc.jpg` |

---

## Configuração de RLS (Row Level Security) no Supabase

Por ser um **bucket público**, qualquer URL funciona sem autenticação — ideal para
fotos de clientes exibidas no sistema interno.

Se quiser adicionar segurança extra, no Supabase → Storage → Policies, crie uma
política que permita leitura pública (`SELECT`) e restrinja escrita (`INSERT`, `UPDATE`, `DELETE`)
ao service role.

---

## Checklist de produção completo

```
[ ] 1. Banco de dados
        Railway → Variables → DATABASE_URL (já configurado)
        python manage.py migrate (rodar uma vez após deploy)

[ ] 2. Storage
        Criar bucket "media" no Supabase (Public)
        Criar S3 Access Keys no Supabase
        Adicionar SUPABASE_S3_* no Railway

[ ] 3. Segurança
        DEBUG=False no Railway
        SECRET_KEY longa e aleatória no Railway

[ ] 4. Superusuário
        python manage.py createsuperuser (rodar uma vez via Railway shell)

[ ] 5. Cron job (verificar vencimentos diariamente)
        No Railway: adicione um Cron Job
        Comando: python manage.py verificar_vencimentos
        Schedule: 0 6 * * *  (todo dia às 6h)
```
