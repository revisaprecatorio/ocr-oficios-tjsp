#!/usr/bin/env python3
"""
Script principal para executar o Sistema OCR - Ofícios Requisitórios TJSP
Configurado com conexão à VPS PostgreSQL.
"""

import os
import sys
import logging
from pathlib import Path

# Configurar variáveis de ambiente
os.environ['OPENAI_API_KEY'] = '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'
os.environ['DB_HOST'] = '72.60.62.124'
os.environ['DB_PORT'] = '5432'
os.environ['DB_NAME'] = 'n8n'
os.environ['DB_USER'] = 'admin'
os.environ['DB_PASSWORD'] = 'BetaAgent2024SecureDB'
os.environ['BASE_DIR'] = './Processos'
os.environ['LOG_LEVEL'] = 'INFO'

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler('ocr_oficios.log')
    ]
)

logger = logging.getLogger(__name__)

def main():
    """Função principal do sistema."""
    logger.info("🚀 SISTEMA OCR - OFÍCIOS REQUISITÓRIOS TJSP")
    logger.info("=" * 60)
    logger.info("Iniciando processamento com conexão à VPS...")
    
    try:
        # Importar módulos
        from app.processador import ProcessadorOficio
        
        # Carregar configurações
        openai_api_key = os.getenv('OPENAI_API_KEY')
        db_config = {
            'host': os.getenv('DB_HOST'),
            'port': int(os.getenv('DB_PORT')),
            'database': os.getenv('DB_NAME'),
            'user': os.getenv('DB_USER'),
            'password': os.getenv('DB_PASSWORD')
        }
        base_dir = os.getenv('BASE_DIR', './Processos')
        
        logger.info(f"📡 Conectando à VPS: {db_config['host']}:{db_config['port']}")
        logger.info(f"🗄️ Database: {db_config['database']}")
        logger.info(f"📂 Diretório base: {base_dir}")
        
        # Validar ambiente
        if not Path(base_dir).exists():
            logger.error(f"❌ Pasta base não encontrada: {base_dir}")
            return
        
        # Contar PDFs disponíveis
        pdf_files = list(Path(base_dir).rglob("*.pdf"))
        if not pdf_files:
            logger.warning(f"⚠️ Nenhum PDF encontrado em: {base_dir}")
            logger.info("Adicione PDFs na estrutura: {base_dir}/{cpf}/{numero_processo}.pdf")
            return
        
        logger.info(f"📄 Encontrados {len(pdf_files)} PDFs para processar")
        
        # Inicializar processador
        logger.info("⚙️ Inicializando processador...")
        processador = ProcessadorOficio(openai_api_key, db_config)
        
        # Processar todos os PDFs
        logger.info("🔄 Iniciando processamento dos PDFs...")
        stats = processador.processar_pasta(base_dir)
        
        # Exibir estatísticas finais
        logger.info("=" * 60)
        logger.info("📊 ESTATÍSTICAS FINAIS")
        logger.info(f"📄 Total de arquivos: {stats['total_arquivos']}")
        logger.info(f"✅ Processados com sucesso: {stats['processados_sucesso']}")
        logger.info(f"❌ Processados com erro: {stats['processados_erro']}")
        logger.info(f"🔍 Ofícios detectados: {stats['oficios_detectados']}")
        logger.info(f"💾 Ofícios salvos no banco: {stats['oficios_salvos']}")
        
        # Calcular taxas de sucesso
        if stats['total_arquivos'] > 0:
            taxa_sucesso = (stats['processados_sucesso'] / stats['total_arquivos']) * 100
            taxa_deteccao = (stats['oficios_detectados'] / stats['total_arquivos']) * 100
            logger.info(f"📈 Taxa de sucesso: {taxa_sucesso:.1f}%")
            logger.info(f"🎯 Taxa de detecção: {taxa_deteccao:.1f}%")
        
        # Mostrar custos estimados (GPT-5 Nano)
        custo_estimado = stats['oficios_detectados'] * 0.00035
        logger.info(f"💰 Custo estimado (GPT-5 Nano): ${custo_estimado:.4f}")
        
        logger.info("=" * 60)
        logger.info("🎉 PROCESSAMENTO CONCLUÍDO COM SUCESSO!")
        logger.info(f"💾 Dados salvos na VPS: {db_config['host']}")
        
    except KeyboardInterrupt:
        logger.info("⚠️ Processamento interrompido pelo usuário")
        sys.exit(1)
    except Exception as e:
        logger.error(f"❌ Erro fatal: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    main()
