# Script PowerShell para fazer push do projeto para GitHub
# Execute este script no PowerShell como administrador

Write-Host "╔═══════════════════════════════════════════════════════════════╗" -ForegroundColor Cyan
Write-Host "║  Script: Enviar App de Fiado para GitHub                    ║" -ForegroundColor Cyan
Write-Host "╚═══════════════════════════════════════════════════════════════╝" -ForegroundColor Cyan

# 1. Verificar se está no diretório correto
$projectPath = "App de fiado\fiado_app"
if (-Not (Test-Path ".\.git")) {
    Write-Host "❌ Erro: Não estou no diretório correto do Git!" -ForegroundColor Red
    Write-Host "Certifique-se de estar em: $projectPath" -ForegroundColor Yellow
    exit 1
}

Write-Host "`n✅ Diretório Git encontrado" -ForegroundColor Green

# 2. Mostrar status atual
Write-Host "`n📊 Status do repositório local:" -ForegroundColor Cyan
git status --short

Write-Host "`n📝 Último commit:" -ForegroundColor Cyan
git log --oneline -1

# 3. Solicitar informações do repositório GitHub
Write-Host "`n📋 Configure seu repositório GitHub:" -ForegroundColor Yellow
$repoName = Read-Host "Nome do repositório (ex: fiado-app)"
$githubUser = Read-Host "Seu usuário GitHub"

if (-Not $repoName -or -Not $githubUser) {
    Write-Host "❌ Nome do repositório ou usuário não fornecido!" -ForegroundColor Red
    exit 1
}

# 4. Construir URL do repositório
$repoUrl = "https://github.com/$githubUser/$repoName.git"
Write-Host "`n🔗 URL do repositório: $repoUrl" -ForegroundColor Cyan

# 5. Adicionar remote
Write-Host "`n⚙️  Adicionando remote 'origin'..." -ForegroundColor Cyan
git remote remove origin 2>$null  # Remover se já existe
git remote add origin $repoUrl

# 6. Renomear branch para 'main'
Write-Host "🌿 Renomeando branch para 'main'..." -ForegroundColor Cyan
git branch -M main

# 7. Fazer push
Write-Host "`n📤 Fazendo push para GitHub..." -ForegroundColor Cyan
Write-Host "Quando solicitada a autenticação:" -ForegroundColor Yellow
Write-Host "  - Para GitHub.com: use seu Personal Access Token (não sua senha)" -ForegroundColor Yellow
Write-Host "  - Gerar em: https://github.com/settings/tokens" -ForegroundColor Yellow
Write-Host ""

git push -u origin main

if ($LASTEXITCODE -eq 0) {
    Write-Host "`n✅ Push realizado com sucesso!" -ForegroundColor Green
    Write-Host "🎉 Seu projeto está agora em: $repoUrl" -ForegroundColor Green
    Write-Host "`n📌 Próximos passos:" -ForegroundColor Cyan
    Write-Host "  1. Acesse o repositório no navegador" -ForegroundColor White
    Write-Host "  2. Crie um README.md com instruções de setup" -ForegroundColor White
    Write-Host "  3. Configure GitHub Secrets para variáveis sensíveis" -ForegroundColor White
} else {
    Write-Host "`n❌ Erro ao fazer push!" -ForegroundColor Red
    Write-Host "Verifique:" -ForegroundColor Yellow
    Write-Host "  1. Se o repositório existe no GitHub" -ForegroundColor White
    Write-Host "  2. Se suas credenciais estão corretas" -ForegroundColor White
    Write-Host "  3. Se tem permissão de escrita no repositório" -ForegroundColor White
}

Write-Host "`nPressione qualquer tecla para sair..." -ForegroundColor Gray
[void][System.Console]::ReadKey($true)
