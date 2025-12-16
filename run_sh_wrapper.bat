@echo off
setlocal

REM === CONFIGURACOES ===
set "PROJ_DIR=C:\Users\Administrator\Documents\revisa\ocr-oficios-tjsp"
set "LOG_FILE=%PROJ_DIR%\logs\bash_exec.log"

REM === CAMINHO DO GIT BASH (VERIFIQUE SE ESTA AQUI MESMO) ===
set "BASH_EXE=C:\Program Files\Git\bin\bash.exe"

if not exist "%BASH_EXE%" (
    echo [ERRO] Git Bash nao encontrado em %BASH_EXE% >> "%LOG_FILE%"
    exit /b 1
)

cd /d "%PROJ_DIR%"

echo [START] Executando pipeline_completo.sh via Git Bash... >> "%LOG_FILE%"

REM === A MÁGICA ACONTECE AQUI ===
REM O "-c" diz para o bash executar o comando entre aspas
"%BASH_EXE%" -c "./pipeline_completo.sh" >> "%LOG_FILE%" 2>&1

echo [END] Finalizado. >> "%LOG_FILE%"