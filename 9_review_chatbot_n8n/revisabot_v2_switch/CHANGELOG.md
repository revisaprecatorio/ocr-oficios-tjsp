# Changelog

## [Stable] 2025-12-09

### Adicionado
- **Save Consulta node**: Novo node PostgreSQL dedicado para persistir dados da consulta e-SAJ
  - Salva: CPF, nome_requerente, processos, total_processos, resposta_formatada
  - Usa UPSERT (ON CONFLICT) para evitar duplicatas
  - Conectado entre `Parse e-SAJ Response` e `Response CPF`

### Corrigido
- **Get User State**: Alterado ordenação de `created_at` para `state_updated_at DESC NULLS LAST`
  - Garante que sempre pega o estado mais recente, independente de qual registro foi criado primeiro
  
- **Response CPF**: Corrigido para usar `$json.responsetext` (minúsculo)
  - PostgreSQL retorna nomes de colunas em minúsculo no RETURNING

- **Parse e-SAJ Response**: Melhorada extração de nome do requerente
  - Função `limparNome()` remove: tags HTML, `&nbsp;`, texto de advogado
  - Múltiplas estratégias de fallback para diferentes formatos de HTML
  - Validação para não aceitar datas como nome

### Testado
- ✅ Fluxo completo: CPF → sim → email → código → pagamento
- ✅ Múltiplos CPFs na mesma sessão
- ✅ Extração de nome: "Elio Rodrigues Barbosa", "Maria Lucia Maduro Pinto"
- ✅ Contagem de processos: 5 e 1 respectivamente

---

## [Checkpoint] 2025-12-09 (anterior)

### Corrigido
- Restauração do workflow após problemas com Update State
- Simplificação do textBody no Send WhatsApp Response

---

## [Initial] 2025-12-08

### Adicionado
- Estrutura inicial do workflow com máquina de estados
- Integração com e-SAJ via HTTP Request
- Roteamento por Switch node
- Verificação de email com código
