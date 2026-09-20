# Diagnostico rapido - versao inline (colar direto no console da VPS)
$BaseDir = "C:\Users\Administrator\Documents\revisa\crawler_tjsp"

function Show($s, $m) {
    $c = switch ($s) {
        "OK"    { "Green" }
        "AVISO" { "Yellow" }
        "ERRO"  { "Red" }
        "INFO"  { "Cyan" }
    }
    Write-Host "[$s] $m" -ForegroundColor $c
}

if (Test-Path $BaseDir) { Show OK "Base encontrado: $BaseDir" } else { Show ERRO "Base NAO encontrado: $BaseDir"; return }

# Arquivos: nome, descricao, OK-se-existir
$map = @(
    @("core\orchestrator_subprocess.py", "Orquestrador ativo", 1),
    @("core\crawler_full.py", "Crawler Selenium", 1),
    @("core\dashboard.py", "App Streamlit", 1),
    @("runtime\executar.bat", "Batch do orquestrador", 1),
    @("run_dashboard.py", "Launcher do dashboard", 1),
    @("run_dashboard.bat", "Batch do dashboard", 1),
    @("worker_pm2.bat", "Batch worker_pm2 (legado)", 1),
    @("start_worker.py", "Launcher start_worker (legado)", 1),
    @("main.py", "main.py na raiz (deve estar ausente)", 0),
    @("orchestrator_subprocess.py", "orchestrator na raiz (deve estar ausente)", 0),
    @("RUNTIME_DISABLED", "Flag RUNTIME_DISABLED (deve estar ausente)", 0)
)

foreach ($m in $map) {
    $p = Join-Path $BaseDir $m[0]
    $ex = Test-Path $p
    if ($m[2] -eq 1) {
        if ($ex) { Show OK "$($m[1]) encontrado" } else { Show ERRO "$($m[1]) NAO encontrado" }
    } else {
        if ($ex) { Show ERRO "$($m[1]) encontrado (inesperado)" } else { Show OK "$($m[1]) confirmado ausente" }
    }
}

# Conteudo dos batches
$rdp = Get-Content "$BaseDir\run_dashboard.py" -Raw -ErrorAction SilentlyContinue
if ($rdp) {
    if ($rdp -match '"dashboard.py"') { Show ERRO "run_dashboard.py aponta para 'dashboard.py' na raiz (nao existe)" } else { Show OK "run_dashboard.py: target OK" }
}

$rdb = Get-Content "$BaseDir\run_dashboard.bat" -Raw -ErrorAction SilentlyContinue
if ($rdb) {
    if ($rdb -match 'dashboard\.py') { Show ERRO "run_dashboard.bat aponta para 'dashboard.py' na raiz (nao existe)" } else { Show OK "run_dashboard.bat: target OK" }
}

$eb = Get-Content "$BaseDir\runtime\executar.bat" -Raw -ErrorAction SilentlyContinue
if ($eb) {
    if ($eb -match 'core\\orchestrator_subprocess\.py') { Show OK "runtime/executar.bat aponta para core/orchestrator_subprocess.py" } else { Show ERRO "runtime/executar.bat nao aponta para o orquestrador correto" }
}

# PM2
if (Get-Command pm2 -ErrorAction SilentlyContinue) {
    Show OK "PM2 encontrado no PATH"
    $pm2 = & pm2 status 2>&1 | Out-String
    Write-Host "`n--- PM2 status ---" -ForegroundColor Cyan
    Write-Host $pm2
    if ($pm2 -match 'painel-visual') { Show ERRO "painel-visual esta no PM2 (verifique a coluna 'restarts'/'↺')" }
    if ($pm2 -match 'worker-pm2|crawler') { Show OK "Processo de crawler encontrado no PM2" } else { Show ERRO "Nenhum processo de crawler encontrado no PM2" }
} else {
    Show AVISO "PM2 nao encontrado no PATH"
}

# Agendador de Tarefas
$t = & schtasks /Query /FO CSV 2>&1 | Out-String
if ($t -match 'crawler|revis|worker|orchestrator|painel') {
    Show INFO "Tarefa relacionada encontrada no Agendador de Tarefas"
} else {
    Show AVISO "Nenhuma tarefa de crawler/revisa encontrada no Agendador"
}

# Processos
Get-Process python,chrome,chromedriver,streamlit -ErrorAction SilentlyContinue | ForEach-Object { Show INFO "$($_.Name) em execucao (PID $($_.Id))" }

# Portas
if (netstat -an | Select-String ':8501\s') { Show OK "Porta 8501 (dashboard Streamlit) esta em uso" } else { Show ERRO "Porta 8501 (dashboard Streamlit) NAO esta em uso" }
if (netstat -an | Select-String ':9222\s') { Show OK "Porta 9222 (Chrome debugger) esta em uso" } else { Show AVISO "Porta 9222 (Chrome debugger) NAO esta em uso" }
