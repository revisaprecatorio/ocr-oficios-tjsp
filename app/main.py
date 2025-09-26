"""
Entry point do Sistema OCR - Ofícios Requisitórios TJSP.
Conforme especificações do AGENTS.md.
"""

import logging
import os
import sys
from pathlib import Path
from dotenv import load_dotenv

from .processador import ProcessadorOficio


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


def carregar_configuracoes():
    """
    Carrega configurações das variáveis de ambiente.
    
    Returns:
        Tuple com (openai_api_key, db_config, base_dir)
    """
    load_dotenv()
    
    # OpenAI API Key
    openai_api_key = os.getenv('OPENAI_API_KEY')
    if not openai_api_key:
        logger.error("OPENAI_API_KEY não configurada")
        sys.exit(1)
    
    # Configurações PostgreSQL
    db_config = {
        'host': os.getenv('DB_HOST', 'localhost'),
        'port': int(os.getenv('DB_PORT', 5432)),
        'database': os.getenv('DB_NAME', 'oficios_tjsp'),
        'user': os.getenv('DB_USER', 'postgres'),
        'password': os.getenv('DB_PASSWORD')
    }
    
    if not db_config['password']:
        logger.error("DB_PASSWORD não configurada")
        sys.exit(1)
    
    # Diretório base
    base_dir = os.getenv('BASE_DIR', './Processos')
    
    logger.info("Configurações carregadas com sucesso")
    return openai_api_key, db_config, base_dir


def validar_ambiente():
    """
    Valida se o ambiente está configurado corretamente.
    """
    # Verificar se pasta Processos existe
    base_dir = os.getenv('BASE_DIR', './Processos')
    if not Path(base_dir).exists():
        logger.error(f"Pasta base não encontrada: {base_dir}")
        logger.info("Criando estrutura de exemplo...")
        Path(base_dir).mkdir(parents=True, exist_ok=True)
        logger.info(f"Pasta criada: {base_dir}")
        logger.info("Adicione os PDFs na estrutura: {base_dir}/{cpf}/{numero_processo}.pdf")
        return False
    
    # Contar PDFs disponíveis
    pdf_files = list(Path(base_dir).rglob("*.pdf"))
    if not pdf_files:
        logger.warning(f"Nenhum PDF encontrado em: {base_dir}")
        logger.info("Adicione PDFs na estrutura: {base_dir}/{cpf}/{numero_processo}.pdf")
        return False
    
    logger.info(f"Encontrados {len(pdf_files)} PDFs para processar")
    return True


def main():
    """
    Função principal do sistema.
    """
    logger.info("=== Sistema OCR - Ofícios Requisitórios TJSP ===")
    logger.info("Iniciando processamento...")
    
    try:
        # Carregar configurações
        openai_api_key, db_config, base_dir = carregar_configuracoes()
        
        # Validar ambiente
        if not validar_ambiente():
            logger.warning("Ambiente não configurado adequadamente")
            return
        
        # Inicializar processador
        logger.info("Inicializando processador...")
        processador = ProcessadorOficio(openai_api_key, db_config)
        
        # Processar todos os PDFs
        logger.info(f"Iniciando processamento da pasta: {base_dir}")
        stats = processador.processar_pasta(base_dir)
        
        # Exibir estatísticas finais
        logger.info("=== ESTATÍSTICAS FINAIS ===")
        logger.info(f"Total de arquivos: {stats['total_arquivos']}")
        logger.info(f"Processados com sucesso: {stats['processados_sucesso']}")
        logger.info(f"Processados com erro: {stats['processados_erro']}")
        logger.info(f"Ofícios detectados: {stats['oficios_detectados']}")
        logger.info(f"Ofícios salvos no banco: {stats['oficios_salvos']}")
        
        # Calcular taxa de sucesso
        if stats['total_arquivos'] > 0:
            taxa_sucesso = (stats['processados_sucesso'] / stats['total_arquivos']) * 100
            taxa_deteccao = (stats['oficios_detectados'] / stats['total_arquivos']) * 100
            logger.info(f"Taxa de sucesso: {taxa_sucesso:.1f}%")
            logger.info(f"Taxa de detecção: {taxa_deteccao:.1f}%")
        
        logger.info("Processamento concluído!")
        
    except KeyboardInterrupt:
        logger.info("Processamento interrompido pelo usuário")
        sys.exit(1)
    except Exception as e:
        logger.error(f"Erro fatal: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
