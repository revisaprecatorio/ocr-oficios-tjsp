#requires -Version 5.1
<#
.SYNOPSIS
    Diagnostico rapido da VPS Windows do Revisa Precatorio.
.DESCRIPTION
    Mostra o que esta rodando (PM2, Task Scheduler, processos), se os arquivos
    criticos existem e se os caminhos estao de acordo com a documentacao.
    NAO altera nada na maquina — so le e reporta.
.PARAMETER BaseDir
    Caminho raiz do crawler_tjsp na VPS.
.EXAMPLE
    .\diagnostico_vps.ps1
    .\diagnostico_vps.ps1 -BaseDir "D:\revisa\crawler_tjsp"
#>
param(
    [string]$BaseDir = "C:\Users\Administrator\Documents\revisa\crawler_tjsp"
)

function Write-Result($Status, $Message) {
    $color = switch ($Status) {
        "OK"    { "Green" }
        "AVISO" { "Yellow" }
        "ERRO"  { "Red" }
        "INFO"  { "Cyan" }
    }
    Write-Host "[$Status] $Message" -ForegroundColor $color
}

function Add-Finding($Findings, $Status, $Message) {
    $Findings.Add([PSCustomObject]@{ Status = $Status; Message = $Message })
    return $Findings
}

$Findings = [System.Collections.Generic.List[object]]::new()

Write-Host "`n==========================================" -ForegroundColor Cyan
Write-Host "  Diagnostico VPS - Revisa Precatorio" -ForegroundColor Cyan
Write-Host "  BaseDir: $BaseDir" -ForegroundColor Cyan
Write-Host "==========================================" -ForegroundColor Cyan

# 1. Diretorio base
if (Test-Path $BaseDir) {
    $Findings = Add-Finding $Findings "OK" "Diretorio base encontrado: $BaseDir"
} else {
    $Findings = Add-Finding $Findings "ERRO" "Diretorio base NAO encontrado: $BaseDir"
}

# 2. Arquivos criticos
$criticalFiles = @(
    @{ Path = "$BaseDir\core\orchestrator_subprocess.py"; Expected = $true; Label = "Orquestrador ativo" },
    @{ Path = "$BaseDir\core\crawler_full.py"; Expected = $true; Label = "Crawler Selenium" },
    @{ Path = "$BaseDir\core\dashboard.py"; Expected = $true; Label = "App Streamlit (core/dashboard.py)" },
    @{ Path = "$BaseDir\runtime\executar.bat"; Expected = $true; Label = "Batch do orquestrador (runtime/executar.bat)" },
    @{ Path = "$BaseDir\run_dashboard.py"; Expected = $true; Label = "Launcher do dashboard (run_dashboard.py)" },
    @{ Path = "$BaseDir\run_dashboard.bat"; Expected = $true; Label = "Batch do dashboard (run_dashboard.bat)" },
    @{ Path = "$BaseDir\worker_pm2.bat"; Expected = $true; Label = "Batch legado worker_pm2.bat" },
    @{ Path = "$BaseDir\start_worker.py"; Expected = $true; Label = "Launcher legado start_worker.py" },
    @{ Path = "$BaseDir\main.py"; Expected = $false; Label = "main.py (deve estar ausente no repo)" },
    @{ Path = "$BaseDir\orchestrator_subprocess.py"; Expected = $false; Label = "orchestrator_subprocess.py na raiz (deve estar em core/)" },
    @{ Path = "$BaseDir\RUNTIME_DISABLED"; Expected = $false; Label = "Flag RUNTIME_DISABLED (se existir bloqueia execucao)" }
)

foreach ($f in $criticalFiles) {
    $exists = Test-Path $f.Path
    if ($f.Expected) {
        if ($exists) {
            $Findings = Add-Finding $Findings "OK" "$($f.Label) encontrado"
        } else {
            $Findings = Add-Finding $Findings "ERRO" "$($f.Label) NAO encontrado: $($f.Path)"
        }
    } else {
        if ($exists) {
            $Findings = Add-Finding $Findings "AVISO" "$($f.Label) encontrado (inesperado): $($f.Path)"
        } else {
            $Findings = Add-Finding $Findings "OK" "$($f.Label) confirmado como ausente"
        }
    }
}

# 3. Conteudo dos batches/laucher aponta para o lugar certo?
if (Test-Path "$BaseDir\run_dashboard.py") {
    $content = Get-Content "$BaseDir\run_dashboard.py" -Raw
    if ($content -match '"core/dashboard.py"') {
        $Findings = Add-Finding $Findings "OK" "run_dashboard.py ja aponta para 'core/dashboard.py'"
    } elseif ($content -match '"dashboard.py"') {
        $Findings = Add-Finding $Findings "ERRO" "run_dashboard.py ainda aponta para 'dashboard.py' na raiz (nao existe)"
    } else {
        $Findings = Add-Finding $Findings "AVISO" "run_dashboard.py: nao foi possivel identificar o target do Streamlit"
    }
}

if (Test-Path "$BaseDir\run_dashboard.bat") {
    $content = Get-Content "$BaseDir\run_dashboard.bat" -Raw
    if ($content -match 'core\\dashboard\.py') {
        $Findings = Add-Finding $Findings "OK" "run_dashboard.bat ja aponta para 'core\dashboard.py'"
    } elseif ($content -match 'dashboard\.py') {
        $Findings = Add-Finding $Findings "ERRO" "run_dashboard.bat ainda aponta para 'dashboard.py' na raiz (nao existe)"
    } else {
        $Findings = Add-Finding $Findings "AVISO" "run_dashboard.bat: nao foi possivel identificar o target do Streamlit"
    }
}

if (Test-Path "$BaseDir\runtime\executar.bat") {
    $content = Get-Content "$BaseDir\runtime\executar.bat" -Raw
    if ($content -match 'core\\orchestrator_subprocess\.py') {
        $Findings = Add-Finding $Findings "OK" "runtime/executar.bat aponta para 'core\orchestrator_subprocess.py'"
    } else {
        $Findings = Add-Finding $Findings "ERRO" "runtime/executar.bat NAO aponta para 'core\orchestrator_subprocess.py'"
    }
}

if (Test-Path "$BaseDir\worker_pm2.bat") {
    $content = Get-Content "$BaseDir\worker_pm2.bat" -Raw
    if ($content -match '\bmain\.py\b') {
        $Findings = Add-Finding $Findings "ERRO" "worker_pm2.bat ainda aponta para 'main.py' (arquivo nao existe)"
    }
}

if (Test-Path "$BaseDir\start_worker.py") {
    $content = Get-Content "$BaseDir\start_worker.py" -Raw
    if ($content -match '"main.py"') {
        $Findings = Add-Finding $Findings "AVISO" "start_worker.py procura 'main.py' na raiz (arquivo nao existe)"
    }
    if ($content -match '"orchestrator_subprocess.py"') {
        $Findings = Add-Finding $Findings "AVISO" "start_worker.py procura 'orchestrator_subprocess.py' na raiz, mas o ativo esta em 'core/'"
    }
}

# 4. PM2
$pm2 = Get-Command pm2 -ErrorAction SilentlyContinue
if ($pm2) {
    $Findings = Add-Finding $Findings "OK" "PM2 encontrado: $($pm2.Source)"
    Write-Host "`n--- PM2 status ---" -ForegroundColor Cyan
    try {
        $pm2Status = & pm2 status 2>&1
        $pm2Status | Out-String | Write-Host

        # Contar restarts e verificar se painel-visual esta em loop
        $painelLine = $pm2Status | Select-String 'painel-visual' | Select-Object -First 1
        if ($painelLine) {
            $fields = $painelLine.Line -split '\|' | ForEach-Object { $_.Trim() } | Where-Object { $_ -ne '' }
            if ($fields.Count -ge 8) {
                $restarts = $fields[7]
                if ($restarts -match '^\d+$') {
                    if ([int]$restarts -gt 10) {
                        $Findings = Add-Finding $Findings "ERRO" "painel-visual esta com $restarts restarts (provavel loop por dashboard.py faltando)"
                    } else {
                        $Findings = Add-Finding $Findings "OK" "painel-visual rodando com $restarts restarts"
                    }
                }
            }
        } else {
            $Findings = Add-Finding $Findings "AVISO" "painel-visual NAO encontrado no PM2"
        }

        if ($pm2Status -match 'worker-pm2|revisabot-crawler|crawler') {
            $Findings = Add-Finding $Findings "INFO" "Processo de crawler encontrado no PM2"
        } else {
            $Findings = Add-Finding $Findings "ERRO" "Nenhum processo de crawler esta rodando no PM2 (worker-pm2 inexistente)"
        }
    } catch {
        $Findings = Add-Finding $Findings "ERRO" "Nao foi possivel obter pm2 status: $_"
    }
} else {
    $Findings = Add-Finding $Findings "AVISO" "PM2 nao encontrado no PATH"
}

# 5. Agendador de Tarefas
Write-Host "`n--- Agendador de Tarefas ---" -ForegroundColor Cyan
$tasks = @()
try {
    $schtasks = & schtasks /Query /FO CSV 2>&1 | ConvertFrom-Csv
    $relevant = $schtasks | Where-Object { $_.'Task Name' -match 'crawler|revis|worker|orchestrator|painel' }
    if ($relevant) {
        $relevant | ForEach-Object {
            $Findings = Add-Finding $Findings "INFO" "Tarefa encontrada: $($_.'Task Name') - Status: $($_.'Last Result')"
            $tasks += $_
        }
        $relevant | Format-Table -AutoSize | Out-String | Write-Host
    } else {
        $Findings = Add-Finding $Findings "AVISO" "Nenhuma tarefa de crawler/revisa encontrada no Agendador"
    }
} catch {
    $Findings = Add-Finding $Findings "AVISO" "Nao foi possivel consultar o Agendador de Tarefas: $_"
}

# 6. Processos do Windows
Write-Host "`n--- Processos relevantes ---" -ForegroundColor Cyan
$procs = @("python", "chrome", "chromedriver", "streamlit")
foreach ($p in $procs) {
    $found = Get-Process -Name $p -ErrorAction SilentlyContinue
    if ($found) {
        $Findings = Add-Finding $Findings "INFO" "$p em execucao (instancias: $($found.Count))"
    } else {
        $Findings = Add-Finding $Findings "AVISO" "$p nao esta em execucao"
    }
}

# 7. Portas
Write-Host "`n--- Portas ---" -ForegroundColor Cyan
$port8501 = $null
$port9222 = $null
try {
    $port8501 = Get-NetTCPConnection -LocalPort 8501 -ErrorAction SilentlyContinue
    $port9222 = Get-NetTCPConnection -LocalPort 9222 -ErrorAction SilentlyContinue
} catch {
    # Fallback para netstat se o cmdlet nao estiver disponivel
    $netstat = netstat -an | Select-String -Pattern ':8501\s'
    if ($netstat) { $port8501 = $true }
    $netstat9222 = netstat -an | Select-String -Pattern ':9222\s'
    if ($netstat9222) { $port9222 = $true }
}

if ($port8501) {
    $Findings = Add-Finding $Findings "OK" "Porta 8501 (dashboard Streamlit) esta em uso"
} else {
    $Findings = Add-Finding $Findings "ERRO" "Porta 8501 (dashboard Streamlit) NAO esta em uso"
}

if ($port9222) {
    $Findings = Add-Finding $Findings "OK" "Porta 9222 (Chrome debugger) esta em uso"
} else {
    $Findings = Add-Finding $Findings "AVISO" "Porta 9222 (Chrome debugger) NAO esta em uso"
}

# 8. Resumo
Write-Host "`n==========================================" -ForegroundColor Cyan
Write-Host "  RESUMO" -ForegroundColor Cyan
Write-Host "==========================================" -ForegroundColor Cyan
$counts = $Findings | Group-Object -Property Status
$counts | ForEach-Object { Write-Host "$($_.Name): $($_.Count)" -ForegroundColor $(switch ($_.Name) { "OK" { "Green" } "AVISO" { "Yellow" } "ERRO" { "Red" } "INFO" { "Cyan" } }) }

$Findings | ForEach-Object { Write-Result $_.Status $_.Message }

Write-Host "`n==========================================" -ForegroundColor Cyan
Write-Host "  RECOMENDACOES (APENAS PARA ANALISE)" -ForegroundColor Cyan
Write-Host "==========================================" -ForegroundColor Cyan
Write-Host @"
1. Corrigir run_dashboard.py e run_dashboard.bat para apontar para 'core/dashboard.py'.
2. Reiniciar 'painel-visual' no PM2 para parar o loop de restarts.
3. Colocar o crawler para rodar com 'runtime/executar.bat' via Agendador de Tarefas
   (a cada 1-5 minutos) ou criar um wrapper controlado para o PM2.
4. Remover/atualizar referencias a 'main.py' (worker_pm2.bat / start_worker.py).
5. Executar este diagnostico novamente apos as correcoes.
"@
