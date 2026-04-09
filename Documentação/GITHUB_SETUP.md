# Configurar Repositório GitHub para o Projeto "App de Fiado"

## Opção 1: Usando GitHub Web Interface (Recomendado)

### Passo 1: Criar Repositório no GitHub
1. Acesse https://github.com/new
2. Preencha:
   - **Repository name**: `fiado-app` (ou nome desejado)
   - **Description**: `Sistema de controle de clientes fiado para restaurante`
   - **Visibility**: `Private` (recomendado para projeto sensível)
3. Clique em **"Create repository"**

### Passo 2: Adicionar Remote ao Git Local

No PowerShell ou CMD, dentro do diretório do projeto:

```powershell
cd "seu_caminho\fiado_app"
git remote add origin https://github.com/seu_usuario/fiado-app.git
git branch -M main
git push -u origin main
```

Quando solicitado, use o **GitHub Personal Access Token** (não sua senha):
1. Acesse https://github.com/settings/tokens
2. Clique em **"Generate new token"** (classic)
3. Selecione escopos: `repo`, `workflow`
4. Copie o token gerado
5. Cole no PowerShell quando solicitado pela senha

---

## Opção 2: Usando GitHub CLI (gh)

### Passo 1: Instalar GitHub CLI

Se não tiver instalado:
```powershell
# Via Chocolatey (se tiver)
choco install gh

# Ou baixe de https://cli.github.com/
```

### Passo 2: Autenticar
```powershell
gh auth login
# Selecione: GitHub.com → HTTPS → Y (para autenticação por browser)
```

### Passo 3: Criar Repositório e Fazer Push
```powershell
cd "seu_caminho\fiado_app"
gh repo create fiado-app --private --source=. --remote=origin --push
```

---

## Verificar Push

Após seguir qualquer opção, verifique se foi bem-sucedido:

```powershell
git remote -v
git log --oneline -5
```

---

## Próximos Passos no Repositório GitHub

1. **Add README.md** com instruções de setup
2. **Configure GitHub Secrets** para variáveis sensíveis (.env)
3. **Enable GitHub Actions** para CI/CD (opcional)
4. **Create Releases** ao alcançar milestones (v1.0-Phase1, v1.1-Phase2, etc)

