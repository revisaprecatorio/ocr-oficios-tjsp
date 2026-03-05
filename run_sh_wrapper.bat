@echo off
setlocal EnableExtensions EnableDelayedExpansion

REM === CONFIGURACOES ===
set "PROJ_DIR=C:\Users\Administrator\Documents\revisa\ocr-oficios-tjsp"
set "BASH_EXE=C:\Program Files\Git\bin\bash.exe"

REM === Script .sh (default) ===
set "SH_TO_RUN=%~1"
if "%SH_TO_RUN%"=="" set "SH_TO_RUN=pipeline_completo.sh"

REM === Parametro extra (CPF) ===
set "CPF_PARAM=%~2"

REM Entra na pasta do projeto
cd /d "%PROJ_DIR%" || exit /b 10

REM Verifica ferramentas
if not exist "%BASH_EXE%" (
    echo [ERRO CRITICO] Git Bash nao encontrado em "%BASH_EXE%"
    exit /b 1
)

if not exist "%PROJ_DIR%\%SH_TO_RUN%" (
    echo [ERRO CRITICO] Script nao encontrado: "%PROJ_DIR%\%SH_TO_RUN%"
    exit /b 2
)

REM === UTF-8 ===
chcp 65001 >nul
set "PYTHONUTF8=1"
set "PYTHONIOENCODING=utf-8"
set "PYTHONLEGACYWINDOWSSTDIO=0"

echo [INFO] Iniciando "%SH_TO_RUN%" com argumento "%CPF_PARAM%"...

REM === EXECUCAO DIRETA ===
REM Removemos o -c e os exports manuais pois o pipeline_completo.sh ja faz isso internamente.
"%BASH_EXE%" "%SH_TO_RUN%" "%CPF_PARAM%"

REM Retorna exit code real
exit /b %ERRORLEVEL%