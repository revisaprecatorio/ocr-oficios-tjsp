#!/usr/bin/env python3
"""
API REST para Sistema OCR - Ofícios Requisitórios TJSP
Compatível com Traefik na VPS
"""

from fastapi import FastAPI, HTTPException, UploadFile, File, BackgroundTasks
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
import os
import asyncio
import logging
from datetime import datetime
from pathlib import Path
import json

# Configurar logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Criar app FastAPI
app = FastAPI(
    title="Sistema OCR - Ofícios Requisitórios TJSP",
    description="API para processamento automático de ofícios requisitórios do TJSP",
    version="1.0.0"
)

# Montar arquivos estáticos se existirem
if os.path.exists("/app/web"):
    app.mount("/static", StaticFiles(directory="/app/web"), name="static")

@app.get("/", response_class=HTMLResponse)
async def root():
    """Página inicial do sistema"""
    return """
    <!DOCTYPE html>
    <html>
    <head>
        <title>Sistema OCR - Ofícios TJSP</title>
        <meta charset="utf-8">
        <style>
            body { font-family: Arial, sans-serif; margin: 40px; }
            .status { color: green; font-weight: bold; }
            .info { background: #f0f8ff; padding: 20px; border-radius: 8px; }
        </style>
    </head>
    <body>
        <h1>🏛️ Sistema OCR - Ofícios Requisitórios TJSP</h1>
        <div class="info">
            <p><strong>Status:</strong> <span class="status">✅ Sistema Ativo</span></p>
            <p><strong>Ambiente:</strong> Produção VPS</p>
            <p><strong>Proxy:</strong> Traefik</p>
            <p><strong>Última atualização:</strong> """ + datetime.now().strftime("%d/%m/%Y %H:%M:%S") + """</p>
        </div>
        
        <h2>📋 Endpoints Disponíveis</h2>
        <ul>
            <li><a href="/health">Health Check</a></li>
            <li><a href="/status">Status do Sistema</a></li>
            <li><a href="/docs">Documentação da API</a></li>
        </ul>
    </body>
    </html>
    """

@app.get("/health")
async def health_check():
    """Health check para Traefik e monitoramento"""
    try:
        # Verificar se consegue importar módulos principais
        from app.detector import DetectorOficio
        from app.processador import ProcessadorOficio
        
        # Verificar variáveis de ambiente essenciais
        required_env = ["OPENAI_API_KEY", "POSTGRES_HOST"]
        missing_env = [var for var in required_env if not os.getenv(var)]
        
        if missing_env:
            raise HTTPException(
                status_code=503, 
                detail=f"Variáveis de ambiente faltando: {missing_env}"
            )
        
        return {
            "status": "healthy",
            "timestamp": datetime.now().isoformat(),
            "service": "ocr-oficios-tjsp",
            "version": "1.0.0"
        }
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        raise HTTPException(status_code=503, detail=f"Service unhealthy: {str(e)}")

@app.get("/status")
async def get_status():
    """Status detalhado do sistema"""
    try:
        # Verificar diretórios
        processos_dir = Path("/app/Processos")
        logs_dir = Path("/app/logs")
        
        # Contar PDFs
        pdf_count = len(list(processos_dir.rglob("*.pdf"))) if processos_dir.exists() else 0
        
        # Verificar logs recentes
        log_file = logs_dir / "ocr_oficios.log"
        last_log_time = None
        if log_file.exists():
            last_log_time = datetime.fromtimestamp(log_file.stat().st_mtime).isoformat()
        
        return {
            "sistema": "OCR Ofícios Requisitórios TJSP",
            "status": "ativo",
            "timestamp": datetime.now().isoformat(),
            "environment": {
                "openai_configured": bool(os.getenv("OPENAI_API_KEY")),
                "database_configured": bool(os.getenv("POSTGRES_HOST")),
                "base_dir": os.getenv("BASE_DIR", "/app/Processos")
            },
            "estatisticas": {
                "pdfs_disponiveis": pdf_count,
                "ultimo_log": last_log_time
            },
            "infraestrutura": {
                "proxy": "Traefik",
                "container": True,
                "hostname": os.getenv("HOSTNAME", "unknown")
            }
        }
    except Exception as e:
        logger.error(f"Status check failed: {e}")
        return {"status": "erro", "error": str(e)}

@app.post("/process")
async def process_pdfs(background_tasks: BackgroundTasks):
    """Trigger manual do processamento de PDFs"""
    try:
        # Adicionar task em background
        background_tasks.add_task(run_ocr_processing)
        
        return {
            "message": "Processamento iniciado em background",
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        logger.error(f"Process trigger failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

async def run_ocr_processing():
    """Executa o processamento OCR em background"""
    try:
        # Importar e executar o sistema principal
        import subprocess
        import sys
        
        logger.info("Iniciando processamento OCR...")
        
        # Executar run_sistema.py
        result = subprocess.run(
            [sys.executable, "/app/run_sistema.py"],
            capture_output=True,
            text=True,
            cwd="/app"
        )
        
        if result.returncode == 0:
            logger.info("Processamento OCR concluído com sucesso")
        else:
            logger.error(f"Processamento OCR falhou: {result.stderr}")
            
    except Exception as e:
        logger.error(f"Erro no processamento OCR: {e}")

@app.get("/logs")
async def get_logs(lines: int = 50):
    """Retorna últimas linhas do log"""
    try:
        log_file = Path("/app/logs/ocr_oficios.log")
        
        if not log_file.exists():
            return {"logs": [], "message": "Arquivo de log não encontrado"}
        
        # Ler últimas linhas
        with open(log_file, 'r', encoding='utf-8') as f:
            all_lines = f.readlines()
            last_lines = all_lines[-lines:] if len(all_lines) > lines else all_lines
        
        return {
            "logs": [line.strip() for line in last_lines],
            "total_lines": len(all_lines),
            "showing": len(last_lines),
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        logger.error(f"Log retrieval failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
