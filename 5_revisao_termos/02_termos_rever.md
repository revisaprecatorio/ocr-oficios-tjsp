# Temos que iremos rever

## 1. Remover Cessão de Crédito
Iremos apenas comentar as linhas, não vamos mexer muito para não quebrar o código. 

## 2. Saldo Final
Iremos extrair mais uma variável chamada "Saldo Final" ela pode existir ou não, encontramos nestas imagens valor_final_apos_pagmento_pagina.png e valor_final_apos_pagmento.png com o corte exato, imagens retiradas de um dos PDFs que estão na amostras /Users/persivalballeste/Documents/@IANIA/PROJECTS/revisa/revisa/3_OCR/5_revisao_termos/04_amostras_pdf 

## 3. Habilitação de Herdeiros
### 3.1 o problema 
A lógica atual é muito simples, ela só busca se o termo existe e acaba dando muitos falso positivos. 
### 3.2 a solução
Necessário entender se a habilitação de herdeiros foi feita para o mesmo CPF (ou pessoa) que está sendo feita a análise, visto que podem haver muitos outros CPFs no documento que não iremos analisar além do CPF objeto. 

### 3.2 nova busca

### 3.2.1 onde identificar a nova busca

#### 3.2.1.2 Local e termo
A imagem no mesmo foler habilitacao_herdeiro.png mostra que existe um termo fixo neste caso sempre escrito "9270 . Habilitação de Herdeiro de Precatório" (o caracter especial no meio é irrelevante, somente precisamos do código "9270" e a palavra no final "Habilitação de Herdeiro de Precatório")

#### 3.2.1.3 
Em seguida abaixo tem uma sessão "Dados da Sucessão", e na 3a linha abaixo tem na esquerda o termo "CPF:" e em seguida o numero do CPF com a máscara formata. 

### 3.2.2 Como validar
O PDF precisa ter o termo conforme descrito acima em 3.2.1.2 Local e termo e o CPF encontraado em 3.2.1.3  ser o mesmo que o CPF objeto.

# 4. Nova coluna na tabela

Precisaremos incluir a coluna "saldo-final" na tabela, é uma coluna nova, que é o valor que iremos capturar no item 2 acima, caso contrário esta coluna será preenchida com o valor_total_requisitado que já é capturado na lógica atual 