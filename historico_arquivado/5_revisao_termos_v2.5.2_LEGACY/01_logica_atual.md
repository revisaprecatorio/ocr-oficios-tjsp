# lógica completa de busca de termos, valores e regras do OCR Atual:

  ---
  📋 LÓGICA ATUAL DE EXTRAÇÃO

  1. TERMOS JURÍDICOS (detector_termos_juridicos.py)

  Onde: Busca no texto completo do PDF via REGEX (case-insensitive)

  3 Termos Detectados:

  | Termo                    | Regex Pattern                                           |
  Campo Schema                 |
  |--------------------------|---------------------------------------------------------|--
  ----------------------------|
  | Preferência              | prefer[eê]ncia                                          |
  preferencial (bool)          |
  | Habilitação de Herdeiros | habilita[çc][aã]o\s+(de|dos)\s+herdeiros                |
  habilitacao_herdeiros (bool) |
  | Cessão de Crédito        | cess[aã]o\s+de\s+(cr[ée]dito|direitos\s+credit[óo]rios) |
  cessao_credito (bool)        |

  Fluxo:
  1. Extrai texto completo do PDF (processador.py:155-159)
  2. Detecta termos via regex (processador.py:162)
  3. Retorna dict {preferencial: bool, habilitacao_herdeiros: bool, cessao_credito: bool}
  4. Após validação Pydantic, injeta esses valores no objeto final
  (processador.py:510-513)

  ---
  2. VALORES E DADOS ESTRUTURADOS (LLM + Prompt)

  Onde: Extração via LLM (GPT-4o-mini ou Gemini) com prompt detalhado

  Campos Extraídos (via _construir_prompt_llm, linha 808):

  Obrigatórios:
  - processo_origem, requerente_caps, numero_ordem
  - Valores financeiros: valor_principal_liquido, valor_principal_bruto, juros_moratorios,
   valor_total_requisitado

  Opcionais:
  - Dados Bancários: banco, agencia, conta, conta_tipo
  - Contribuições: contrib_previdenciaria_iprem, contrib_previdenciaria_hspm
  - Datas: data_nascimento, data_base_atualizacao, data_ajuizamento, data_transito_julgado
  - Preferências: idoso (≥60 anos, calculado), doenca_grave, pcd
  - Outros: vara, credor_nome, credor_cpf_cnpj, advogado_nome, etc.

  Regras Críticas no Prompt:
  - Valores brasileiros (ponto=milhar, vírgula=decimal) → convertidos
  - PDFs multi-creditor: prioriza "Nome:" do ofício vs "Requerente:" do PROCESSAMENTO
  - Dados inline vs ANEXO II separado
  - Validação líquido ≤ bruto
