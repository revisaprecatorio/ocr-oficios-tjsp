📋 PLANO DE IMPLEMENTAÇÃO - Revisão de Termos e Extração (v2.5.2)                      │ │
│ │                                                                                        │ │
│ │ 🎯 RESUMO DAS MUDANÇAS                                                                 │ │
│ │                                                                                        │ │
│ │ 1. REMOVER: Cessão de Crédito                                                          │ │
│ │                                                                                        │ │
│ │ - ❌ Comentar detecção de cessao_credito (não deletar código)                           │ │
│ │ - Manter campo no banco (compatibilidade)                                              │ │
│ │                                                                                        │ │
│ │ 2. ADICIONAR: Saldo Final                                                              │ │
│ │                                                                                        │ │
│ │ - ✅ Novo campo saldo_final (NUMERIC(15,2))                                             │ │
│ │ - Lógica: Se encontrar "Saldo Final" no PDF → extrair valor, senão → copiar            │ │
│ │ valor_total_requisitado                                                                │ │
│ │                                                                                        │ │
│ │ 3. MELHORAR: Habilitação de Herdeiros (evitar falso-positivos)                         │ │
│ │                                                                                        │ │
│ │ - ⚠️ Problema atual: Busca simples retorna TRUE para qualquer CPF no PDF               │ │
│ │ - ✅ Nova lógica: Validar se CPF do objeto = CPF da habilitação                         │ │
│ │                                                                                        │ │
│ │ 4. ATUALIZAR: Banco de Dados                                                           │ │
│ │                                                                                        │ │
│ │ - Nova coluna saldo_final após valor_total_requisitado                                 │ │
│ │ - Migration script para adicionar coluna                                               │ │
│ │                                                                                        │ │
│ │ ---                                                                                    │ │
│ │ 📝 DETALHAMENTO POR ETAPA                                                              │ │
│ │                                                                                        │ │
│ │ ETAPA 1: Detector de Termos Jurídicos (detector_termos_juridicos.py)                   │ │
│ │                                                                                        │ │
│ │ 1.1. Comentar Cessão de Crédito                                                        │ │
│ │                                                                                        │ │
│ │ # Linhas 46-51: COMENTAR pattern_cessao                                                │ │
│ │ # Linhas 86-88: COMENTAR detecção cessao                                               │ │
│ │ # Linhas 162-168: COMENTAR detecção com contexto                                       │ │
│ │ # Manter estrutura do dict retornando sempre False                                     │ │
│ │                                                                                        │ │
│ │ 1.2. Melhorar Habilitação de Herdeiros                                                 │ │
│ │                                                                                        │ │
│ │ Novo método: detectar_habilitacao_validada(texto_pdf, cpf_objeto)                      │ │
│ │                                                                                        │ │
│ │ Lógica de detecção:                                                                    │ │
│ │ 1. Buscar padrão: 9270 + Habilitação de Herdeiro de Precatório                         │ │
│ │ 2. Extrair seção "Dados da Sucessão" (próximas 20 linhas)                              │ │
│ │ 3. Buscar linha com CPF: seguido do CPF formatado                                      │ │
│ │ 4. Validar se CPF encontrado == CPF objeto (sem formatação)                            │ │
│ │ 5. Retornar TRUE apenas se ambos critérios atenderem                                   │ │
│ │                                                                                        │ │
│ │ Regex sugerido:                                                                        │ │
│ │ # Pattern 1: Identificar seção de habilitação                                          │ │
│ │ pattern_hab_codigo = r'9270\s*[.\-–]*\s*Habilita[çc][aã]o\s+de\s+Herdeiro'             │ │
│ │                                                                                        │ │
│ │ # Pattern 2: Extrair CPF da seção "Dados da Sucessão"                                  │ │
│ │ pattern_cpf_sucessao = r'CPF:\s*(\d{3}\.\d{3}\.\d{3}-\d{2})'                           │ │
│ │                                                                                        │ │
│ │ ---                                                                                    │ │
│ │ ETAPA 2: Extração Saldo Final (LLM + Regex)                                            │ │
│ │                                                                                        │ │
│ │ 2.1. Detector Regex (nova classe DetectorSaldoFinal)                                   │ │
│ │                                                                                        │ │
│ │ Arquivo: 1_parsing_PDF/app/detector_saldo_final.py                                     │ │
│ │                                                                                        │ │
│ │ Padrões identificados nas imagens:                                                     │ │
│ │ - "Saldo final após pagamento:" + valor                                                │ │
│ │ - "Saldo Final:" + valor                                                               │ │
│ │ - Contexto: Aparece em tabelas DEPRE após pagamentos parciais                          │ │
│ │                                                                                        │ │
│ │ Regex sugerido:                                                                        │ │
│ │ pattern_saldo_final =                                                                  │ │
│ │ r'Saldo\s+[Ff]inal\s*(?:após\s+pagamento)?:?\s*R?\$?\s*([\d.,]+)'                      │ │
│ │                                                                                        │ │
│ │ 2.2. Prompt LLM (adicionar ao _construir_prompt_llm)                                   │ │
│ │                                                                                        │ │
│ │ Adicionar após linha 1021 (seção "OUTROS VALORES"):                                    │ │
│ │ - saldo_final: Saldo final após pagamento parcial (número)                             │ │
│ │   ⚠️ ATENÇÃO: Este campo aparece APENAS se houve pagamento parcial anterior            │ │
│ │   Procure por: "Saldo final após pagamento:", "Saldo Final:", tabelas DEPRE            │ │
│ │   Se NÃO encontrar, retorne null                                                       │ │
│ │                                                                                        │ │
│ │ 2.3. Lógica de Fallback (processador.py)                                               │ │
│ │                                                                                        │ │
│ │ Após validação Pydantic (linha ~513):                                                  │ │
│ │ # Calcular saldo_final                                                                 │ │
│ │ if not oficio_validado.saldo_final:                                                    │ │
│ │     # Fallback: usar valor_total_requisitado                                           │ │
│ │     oficio_validado.saldo_final = oficio_validado.valor_total_requisitado              │ │
│ │     logger.info("📊 Saldo final não encontrado, usando valor_total_requisitado")       │ │
│ │                                                                                        │ │
│ │ ---                                                                                    │ │
│ │ ETAPA 3: Schema Pydantic (schemas.py)                                                  │ │
│ │                                                                                        │ │
│ │ 3.1. Adicionar campo saldo_final                                                       │ │
│ │                                                                                        │ │
│ │ Após linha 165 (valor_total_requisitado):                                              │ │
│ │ saldo_final: Optional[Decimal] = Field(                                                │ │
│ │     None,                                                                              │ │
│ │     description="Saldo final após pagamento parcial (se houver), senão igual a         │ │
│ │ valor_total_requisitado"                                                               │ │
│ │ )                                                                                      │ │
│ │                                                                                        │ │
│ │ 3.2. Adicionar ao validator arredondar_decimais                                        │ │
│ │                                                                                        │ │
│ │ Linha 313: adicionar 'saldo_final' na lista                                            │ │
│ │                                                                                        │ │
│ │ ---                                                                                    │ │
│ │ ETAPA 4: Banco de Dados                                                                │ │
│ │                                                                                        │ │
│ │ 4.1. Migration SQL (novo arquivo)                                                      │ │
│ │                                                                                        │ │
│ │ Arquivo: 2_ingestao/sql/03_add_saldo_final.sql                                         │ │
│ │ -- Adicionar coluna saldo_final                                                        │ │
│ │ ALTER TABLE esaj_detalhe_processos                                                     │ │
│ │ ADD COLUMN IF NOT EXISTS saldo_final NUMERIC(15,2);                                    │ │
│ │                                                                                        │ │
│ │ -- Comentário                                                                          │ │
│ │ COMMENT ON COLUMN esaj_detalhe_processos.saldo_final IS                                │ │
│ │ 'Saldo final após pagamento parcial. Se não houver pagamento parcial, igual a          │ │
│ │ valor_total_requisitado';                                                              │ │
│ │                                                                                        │ │
│ │ -- Preencher valores NULL com valor_total_requisitado (dados existentes)               │ │
│ │ UPDATE esaj_detalhe_processos                                                          │ │
│ │ SET saldo_final = valor_total_requisitado                                              │ │
│ │ WHERE saldo_final IS NULL;                                                             │ │
│ │                                                                                        │ │
│ │ 4.2. Script Python (novo arquivo)                                                      │ │
│ │                                                                                        │ │
│ │ Arquivo: 2_ingestao/scripts/add_saldo_final_column.py                                  │ │
│ │ - Executa migration SQL                                                                │ │
│ │ - Valida coluna criada                                                                 │ │
│ │ - Relatório de registros atualizados                                                   │ │
│ │                                                                                        │ │
│ │ ---                                                                                    │ │
│ │ ETAPA 5: Processador (processador.py)                                                  │ │
│ │                                                                                        │ │
│ │ 5.1. Integrar DetectorSaldoFinal                                                       │ │
│ │                                                                                        │ │
│ │ Linha ~59: Importar e inicializar detector                                             │ │
│ │                                                                                        │ │
│ │ 5.2. Injetar termos jurídicos atualizados                                              │ │
│ │                                                                                        │ │
│ │ Linha 162: Passar CPF para detectar_termos(texto_completo, cpf_formatado)              │ │
│ │                                                                                        │ │
│ │ Linha 510-513: Atualizar injeção de termos:                                            │ │
│ │ # cessao_credito sempre False (desativado)                                             │ │
│ │ oficio_validado.habilitacao_herdeiros = termos_juridicos['habilitacao_herdeiros']      │ │
│ │ oficio_validado.preferencial = termos_juridicos['preferencial']                        │ │
│ │ oficio_validado.cessao_credito = False  # DESATIVADO v2.5.2                            │ │
│ │                                                                                        │ │
│ │ 5.3. Calcular saldo_final                                                              │ │
│ │                                                                                        │ │
│ │ Após linha 513:                                                                        │ │
│ │ # Calcular saldo_final (fallback)                                                      │ │
│ │ if not oficio_validado.saldo_final and oficio_validado.valor_total_requisitado:        │ │
│ │     oficio_validado.saldo_final = oficio_validado.valor_total_requisitado              │ │
│ │                                                                                        │ │
│ │ ---                                                                                    │ │
│ │ 🧪 CASOS DE TESTE                                                                      │ │
│ │                                                                                        │ │
│ │ Teste 1: Habilitação de Herdeiros - TRUE                                               │ │
│ │                                                                                        │ │
│ │ - CPF: 576.290.808-91 (doc_47860430.pdf)                                               │ │
│ │ - Esperado: habilitacao_herdeiros = TRUE                                               │ │
│ │ - Validação: Código 9270 + CPF 576.290.808-91 em "Dados da Sucessão"                   │ │
│ │                                                                                        │ │
│ │ Teste 2: Habilitação de Herdeiros - FALSE (outro CPF)                                  │ │
│ │                                                                                        │ │
│ │ - CPF: 105.823.048-49 (doc_58276729.pdf - Jorge de Souza Lima)                         │ │
│ │ - Esperado: habilitacao_herdeiros = FALSE                                              │ │
│ │ - Razão: Documento sobre outro titular (não há habilitação para este CPF)              │ │
│ │                                                                                        │ │
│ │ Teste 3: Saldo Final - Presente                                                        │ │
│ │                                                                                        │ │
│ │ - CPF: 284.552.608-31 (pagamento parcial)                                              │ │
│ │ - Esperado: saldo_final = [valor extraído da tabela DEPRE]                             │ │
│ │                                                                                        │ │
│ │ Teste 4: Saldo Final - Ausente                                                         │ │
│ │                                                                                        │ │
│ │ - CPF: 365.764.148-38                                                                  │ │
│ │ - Esperado: saldo_final = valor_total_requisitado (fallback)                           │ │
│ │                                                                                        │ │
│ │ Teste 5: Cessão de Crédito - Desativado                                                │ │
│ │                                                                                        │ │
│ │ - Todos os CPFs                                                                        │ │
│ │ - Esperado: cessao_credito = FALSE (sempre)                                            │ │
│ │                                                                                        │ │
│ │ ---                                                                                    │ │
│ │ 📊 ARQUIVOS IMPACTADOS                                                                 │ │
│ │                                                                                        │ │
│ │ Novos Arquivos (5)                                                                     │ │
│ │                                                                                        │ │
│ │ 1. 1_parsing_PDF/app/detector_saldo_final.py (novo detector)                           │ │
│ │ 2. 2_ingestao/sql/03_add_saldo_final.sql (migration)                                   │ │
│ │ 3. 2_ingestao/scripts/add_saldo_final_column.py (script migration)                     │ │
│ │ 4. tests/test_detector_saldo_final.py (testes)                                         │ │
│ │ 5. tests/test_habilitacao_validada.py (testes nova lógica)                             │ │
│ │                                                                                        │ │
│ │ Modificados (6)                                                                        │ │
│ │                                                                                        │ │
│ │ 1. 1_parsing_PDF/app/detector_termos_juridicos.py (comentar cessão + nova habilitação) │ │
│ │ 2. 1_parsing_PDF/app/schemas.py (add saldo_final)                                      │ │
│ │ 3. 1_parsing_PDF/app/processador.py (integrar detectores + fallback)                   │ │
│ │ 4. 1_parsing_PDF/app/processador_v3.py (herdar mudanças)                               │ │
│ │ 5. 2_ingestao/sql/01_create_table.sql (add coluna saldo_final)                         │ │
│ │ 6. 2_ingestao/scripts/create_table.py (documentar nova coluna)                         │ │
│ │                                                                                        │ │
│ │ ---                                                                                    │ │
│ │ ⚠️ COMPATIBILIDADE                                                                     │ │
│ │                                                                                        │ │
│ │ Banco de Dados                                                                         │ │
│ │                                                                                        │ │
│ │ - ✅ Nova coluna saldo_final é OPCIONAL (permite NULL)                                  │ │
│ │ - ✅ Migration preenche registros antigos com fallback                                  │ │
│ │ - ✅ Campo cessao_credito mantido (não quebra queries existentes)                       │ │
│ │                                                                                        │ │
│ │ Código Legado                                                                          │ │
│ │                                                                                        │ │
│ │ - ✅ cessao_credito apenas comentado (não deletado)                                     │ │
│ │ - ✅ Fallback garante saldo_final sempre preenchido                                     │ │
│ │ - ✅ Habilitação antiga ainda funciona, nova lógica é mais precisa                      │ │
│ │                                                                                        │ │
│ │ ---                                                                                    │ │
│ │ 🚀 ORDEM DE EXECUÇÃO                                                                   │ │
│ │                                                                                        │ │
│ │ 1. Banco: Rodar migration SQL (add coluna saldo_final)                                 │ │
│ │ 2. Código: Atualizar schemas.py, detector_termos_juridicos.py                          │ │
│ │ 3. Código: Criar detector_saldo_final.py                                               │ │
│ │ 4. Código: Atualizar processador.py, processador_v3.py                                 │ │
│ │ 5. Testes: Rodar testes com 14 PDFs de amostra                                         │ │
│ │ 6. Validação: Reprocessar 14 casos da tabela de amostras                               │ │
│ │ 7. Deploy: Commit + documentação ByteRover             