@echo off
REM Script de Teste Completo do Pipeline - Windows Server 2022
REM Testa ETAPA 1 (PDFs -> JSONs) com 3 PDFs reais
REM
REM Uso:
REM   teste_pipeline_completo.bat

setlocal enabledelayedexpansion

echo ╔════════════════════════════════════════════════════════════════╗
echo ║  TESTE COMPLETO DO PIPELINE - Ofícios Requisitórios TJSP       ║
echo ╚════════════════════════════════════════════════════════════════╝
echo.

REM Verificar .env
if not exist .env (
    echo ❌ Arquivo .env não encontrado!
    echo    Copie .env.example e configure OPENAI_API_KEY
    exit /b 1
)

REM Carregar variáveis do .env (simplificado para Windows)
for /f "tokens=1,2 delims==" %%a in (.env) do (
    if "%%a"=="OPENAI_API_KEY" set OPENAI_API_KEY=%%b
)

if "%OPENAI_API_KEY%"=="" (
    echo ❌ OPENAI_API_KEY não configurada no .env!
    exit /b 1
)

echo ✓ Configurações carregadas de .env
echo.

REM Limpar diretório de output de testes anteriores
echo ═══════════════════════════════════════════════════════════════
echo 1. LIMPEZA DE OUTPUTS ANTERIORES
echo ═══════════════════════════════════════════════════════════════

if exist output_teste (
    echo Removendo output_teste anterior...
    rmdir /s /q output_teste
)

echo ✓ Diretório limpo
echo.

REM ETAPA 1: Exportar JSONs (apenas 3 PDFs para teste)
echo ═══════════════════════════════════════════════════════════════
echo 2. ETAPA 1: PDFs -^> JSONs (3 PDFs de teste)
echo ═══════════════════════════════════════════════════════════════

python exportar_json.py --input data\consultas --output output_teste --limite 3

if errorlevel 1 (
    echo ❌ ETAPA 1 falhou!
    exit /b 1
)

echo ✓ ETAPA 1 concluída com sucesso
echo.

REM Verificar JSONs gerados
echo ═══════════════════════════════════════════════════════════════
echo 3. VERIFICAÇÃO DOS JSONs GERADOS
echo ═══════════════════════════════════════════════════════════════

set TOTAL_JSONS=0
for /r output_teste\json %%f in (*.json) do set /a TOTAL_JSONS+=1

echo Total de JSONs gerados: %TOTAL_JSONS%

if %TOTAL_JSONS%==0 (
    echo ❌ Nenhum JSON gerado!
    exit /b 1
)

echo.
echo JSONs gerados:
for /r output_teste\json %%f in (*.json) do echo   - %%f

echo.
echo Amostra do primeiro JSON:
for /r output_teste\json %%f in (*.json) do (
    echo Arquivo: %%f
    echo ---
    python -m json.tool %%f | more
    goto :continue
)
:continue

echo.
echo ✓ JSONs verificados
echo.

REM Mostrar estatísticas
echo ═══════════════════════════════════════════════════════════════
echo 4. ESTATÍSTICAS DO PROCESSAMENTO
echo ═══════════════════════════════════════════════════════════════

if exist output_teste\estatisticas.json (
    python -m json.tool output_teste\estatisticas.json
) else (
    echo ⚠️  Arquivo de estatísticas não encontrado
)

echo.

REM Verificar se algum JSON tem dados bancários
echo ═══════════════════════════════════════════════════════════════
echo 5. VERIFICAÇÃO DE DADOS BANCÁRIOS (ANEXO II)
echo ═══════════════════════════════════════════════════════════════

set COM_BANCO=0
for /r output_teste\json %%f in (*.json) do (
    findstr /c:"\"banco\"" %%f >nul
    if not errorlevel 1 (
        echo ✓ %%f contém dados bancários
        set /a COM_BANCO+=1
    )
)

echo.
echo JSONs com dados bancários: %COM_BANCO%/%TOTAL_JSONS%

if %COM_BANCO%==0 (
    echo ⚠️  Nenhum ANEXO II detectado (normal se PDFs não tiverem)
)

echo.

REM Resumo final
echo ╔════════════════════════════════════════════════════════════════╗
echo ║                         TESTE CONCLUÍDO                        ║
echo ╚════════════════════════════════════════════════════════════════╝
echo.
echo Resultados salvos em: output_teste\
echo.
echo ✓ PIPELINE TESTADO COM SUCESSO!
echo.
echo Próximos passos:
echo   1. Revisar JSONs em: output_teste\json\
echo   2. Se OK, processar todos: python exportar_json.py --input data\consultas --output output
echo   3. Importar PostgreSQL: python importar_postgres.py --input output\json
echo.

endlocal
