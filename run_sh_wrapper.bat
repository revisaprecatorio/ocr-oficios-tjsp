@echo off
setlocal EnableExtensions EnableDelayedExpansion

REM === CONFIGURACOES ===
set "PROJ_DIR=C:\Users\Administrator\Documents\revisa\ocr-oficios-tjsp"
set "BASH_EXE=C:\Program Files\Git\bin\bash.exe"

REM === Script .sh (default) ===
set "SH_TO_RUN=%~1"
if "%SH_TO_RUN%"=="" set "SH_TO_RUN=pipeline_completo.sh"

REM Entra na pasta do projeto
cd /d "%PROJ_DIR%"

REM Verifica ferramentas
if not exist "%BASH_EXE%" (
    echo [ERRO CRITICO] Git Bash nao encontrado em "%BASH_EXE%"
    pause
    exit /b 1
)

if not exist "%PROJ_DIR%\%SH_TO_RUN%" (
    echo [ERRO CRITICO] Script nao encontrado: "%PROJ_DIR%\%SH_TO_RUN%"
    pause
    exit /b 2
)

REM === Configura UTF-8 para o console ===
chcp 65001 >nul
set "PYTHONUTF8=1"
set "PYTHONIOENCODING=utf-8"
set "PYTHONLEGACYWINDOWSSTDIO=0"

echo.
echo ========================================================
echo [START] Executando "%SH_TO_RUN%" (MODO VISUAL)...
echo ========================================================
echo.

REM === EXECUÇÃO SEM LOG ESCONDIDO ===
"%BASH_EXE%" -c "export LANG=C.UTF-8; export LC_ALL=C.UTF-8; set -e; bash \"%SH_TO_RUN%\""

echo.
echo ========================================================
echo [END] Processo finalizado.
echo ========================================================
echo.

REM Pausa para voce ler o erro se a janela tentar fechar
pause