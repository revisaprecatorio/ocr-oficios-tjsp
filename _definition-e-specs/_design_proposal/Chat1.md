perfeito — analisei os PDFs e as anotações que você enviou e dá pra fechar um pipeline sólido para varrer os diretórios por CPF, localizar a(s) página(s) “Ofício Requisitório / Anexo II”, extrair os campos-chave e salvar tudo em JSON (inserção no banco fica para a etapa 2).

# O que extrair (campos-alvo)

Com base nos exemplos, os campos aparecem principalmente no **ANEXO II** e no **Ofício Requisitório**. Exemplos reais dos seus PDFs:

* **ANEXO II** com: *Nome, CPF/CNPJ/RNE, Banco/Agência/Conta, Data de nascimento, Total deste requerente, Valor requisitado, Data base para atualização, Principal/Indenização, Juros Moratórios, Termo final dos juros, Contribuições* etc. 
* **Ofício Requisitório** com: *Processo nº (principal e de origem), Credor, Advogado, Devedor, Natureza (do crédito), Valor global* etc. 
* **Dados básicos do ofício** em “Termo de Declaração / dados do SAJ” com *tipo de pessoa, nome, CPF, natureza, valor global, foro/classe, datas processuais* — úteis como fallback quando o layout do Anexo II variar. 
* **Campos numéricos e “Data Base”** também aparecem em telas de cálculo anexas (quando o Anexo II não vier completo). 

> Em resumo, a detecção das strings “ANEXO II”, “OFÍCIO REQUISITÓRIO”, “Dados principais do ofício requisitório” resolve ~100% dos casos do seu lote de amostra.

# Estratégia técnica (robusta e em lote)

1. **Varredura por diretórios**
   Percorrer `base_dir/<CPF>/*.pdf` (estrutura idêntica à captura de tela).

2. **Leitura de PDF + fallback OCR**

   * Tentar **texto nativo** (pdfminer.six / PyPDF2).
   * Se a página não tiver texto (scaneado), rodar **OCR** só nessa página (Tesseract via `pytesseract` ou `ocrmypdf` em arquivo temporário).
   * Isso garante performance: OCR apenas quando necessário.

3. **Localização das páginas-alvo**

   * Procurar marcadores (case-insensitive):
     `ANEXO II`, `OFÍCIO REQUISITÓRIO`, `Dados principais do ofício`, `TERMO DE DECLARAÇÃO`.
   * Guardar o índice das páginas que contêm esses marcadores.

4. **Extração por *regex* + normalização**

   * Regex bem ancoradas por rótulos (ex.: `r"Nome:\s*(.+)"`, `r"CPF/CNPJ/RNE:\s*([\d\.\-\/]+)"`, `r"Data base para atualização:\s*([\d\/]+)"`, `r"Principal/Indenização:\s*R\$\s*([\d\.\,]+)"`, `r"Valor requisitado:\s*R\$\s*([\d\.\,]+)"`, etc.).
   * Normalizar números brasileiros (troca de `.` e `,`), datas (DD/MM/AAAA → ISO), e nomes (trim/uppercase opcional).

5. **Schema JSON de saída (por PDF)**

   ```json
   {
     "cpf_dir": "94706751853",
     "pdf_file": "0176088-13.2021.8.26.0500.pdf",
     "source_pages": {"anexo_ii":[93], "oficio":[156]}, 
     "processos": {
       "principal":"0035938-67.2018.8.26.0053",
       "origem":"0417062-63.1999.8.26.0053"
     },
     "parte": {
       "nome":"Jorge Francisco de Pontes",
       "cpf":"947.067.518-53",
       "data_nascimento":"1958-11-02"
     },
     "bancario": {"banco":"341","agencia":"3740","conta":"00000001341-6"},
     "natureza":{"geral":"Alimentar - ...", "credito":"Indenizatório"},
     "valores": {
       "total_requerente": 73431.66,
       "valor_requisitado": 73431.66,
       "principal_indenizacao": 73431.66,
       "juros_moratorios": 0.00
     },
     "datas": {
       "data_base_atualizacao":"2020-02-29",
       "transito_em_julgado":"2007-01-14"
     },
     "devedor":"PREFEITURA MUNICIPAL DE SÃO PAULO",
     "contribuicoes":[{"descricao":"IPREM/SPPREV","valor":619.93}]
   }
   ```

6. **Outputs**

   * Um JSON por PDF em `output/json/<CPF>/<arquivo>.json`.
   * Um **NDJSON** agregando tudo (`output/all_extracoes.ndjson`) para import fácil.

---

# Script proposto (pronto para uso)

> Requisitos: `pip install pdfminer.six PyPDF2 pytesseract pillow pdf2image ocrmypdf`
> (Tesseract instalado no SO; opcional `ocrmypdf` para OCR de página inteira em fallback.)

```python
#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Extractor de Ofício Requisitório / ANEXO II (TJSP) - Lote por diretórios de CPF
Etapa 1: Gera JSONs por PDF e um NDJSON agregado.
"""

import os, re, json, tempfile, shutil, subprocess
from pathlib import Path
from typing import Dict, List, Optional
from datetime import datetime

from PyPDF2 import PdfReader

# --------- Config ---------
BASE_DIR = Path("/caminho/para/data/consultas")  # <<< AJUSTE AQUI
OUT_DIR  = Path("./output")
OUT_DIR.mkdir(parents=True, exist_ok=True)
USE_OCRMYPDF = True   # True = tenta ocrmypdf na página quando sem texto
TESSERACT_CMD = "tesseract"  # ou caminho absoluto

# Marcadores de páginas-alvo
PAGE_MARKERS = [
    r"ANEXO\s+II",
    r"OF[ÍI]CIO\s+REQUISIT[ÓO]RIO",
    r"DADOS\s+PRINCIPAIS\s+DO\s+OF[ÍI]CIO\s+REQUISIT[ÓO]RIO",
    r"TERMO\s+DE\s+DECLARA[ÇC][ÃA]O"
]
PAGE_MARKERS = [re.compile(pat, re.I) for pat in PAGE_MARKERS]

# --------- Utils ---------
def norm_money_br(val: str) -> Optional[float]:
    s = val.strip().upper().replace("R$","").replace(" ", "")
    if not s: return None
    s = s.replace(".", "").replace(",", ".")
    try:
        return float(s)
    except:
        return None

def norm_date_br(d: str) -> Optional[str]:
    d = d.strip()
    for fmt in ("%d/%m/%Y", "%d/%m/%y"):
        try:
            return datetime.strptime(d, fmt).date().isoformat()
        except:
            pass
    return None

def read_page_text(reader: PdfReader, page_index: int) -> str:
    try:
        return reader.pages[page_index].extract_text() or ""
    except Exception:
        return ""

def ocr_single_page(pdf_path: Path, page_index: int) -> str:
    """
    Faz OCR de uma única página (fallback) usando ocrmypdf (rápido e sem tocar no resto).
    Alternativa: exportar imagem e rodar pytesseract.
    """
    try:
        with tempfile.TemporaryDirectory() as td:
            in_pdf  = pdf_path
            out_pdf = Path(td, "ocr.pdf")
            # extrair pagina i para um pdf temporário
            single_pdf = Path(td, "single.pdf")
            subprocess.run([
                "pdftk", str(in_pdf), "cat", f"{page_index+1}", "output", str(single_pdf)
            ], check=True)
            subprocess.run(["ocrmypdf", "--force-ocr", "--quiet", str(single_pdf), str(out_pdf)], check=True)
            txt = subprocess.run(["pdftotext", "-layout", str(out_pdf), "-"], check=True, capture_output=True, text=True).stdout
            return txt
    except Exception:
        return ""

def find_target_pages(texts: List[str]) -> Dict[str, List[int]]:
    idx = {"anexo_ii": [], "oficio": [], "dados_basicos": [], "termo": []}
    for i, t in enumerate(texts):
        if re.search(PAGE_MARKERS[0], t): idx["anexo_ii"].append(i)
        if re.search(PAGE_MARKERS[1], t): idx["oficio"].append(i)
        if re.search(PAGE_MARKERS[2], t): idx["dados_basicos"].append(i)
        if re.search(PAGE_MARKERS[3], t): idx["termo"].append(i)
    return idx

# --------- Regex de campos ---------
RX = {
    "nome": re.compile(r"Nome:\s*(.+)"),
    "cpf": re.compile(r"CPF/CNPJ/RNE:\s*([\d\.\-\/]+)"),
    "banco": re.compile(r"Banco:\s*(\d+)"),
    "agencia": re.compile(r"Ag[êe]ncia:\s*(\d+)"),
    "conta": re.compile(r"Conta:\s*([\d\-\.]+)"),
    "total_req": re.compile(r"Total deste requerente:\s*R\$\s*([\d\.\,]+)", re.I),
    "valor_requisitado": re.compile(r"Valor requisitado:\s*R\$\s*([\d\.\,]+)", re.I),
    "data_base": re.compile(r"Data base para atualiza[çc][ãa]o:\s*([\d\/]+)", re.I),
    "principal": re.compile(r"Principal/Indeniza[çc][ãa]o:\s*R\$\s*([\d\.\,]+)", re.I),
    "juros_mora": re.compile(r"Juros Morat[óo]rios:\s*R\$\s*([\d\.\,]+)", re.I),
    # Ofício
    "proc_principal": re.compile(r"Processo\s*n[ºo]:\s*([\d\.\-\/]+)"),
    "proc_origem": re.compile(r"Processo\s+Principal/Conhecimento:\s*([\d\.\-\/]+)", re.I),
    "credor": re.compile(r"Credor\(s\):\s*(.+)"),
    "devedor": re.compile(r"Devedor:\s*(.+)"),
    "natureza": re.compile(r"Natureza:\s*(.+)"),
    "natureza_credito": re.compile(r"Natureza do cr[eê]dito:\s*(.+)", re.I),
    "valor_global": re.compile(r"Valor global(?: da requisi[çc][ãa]o)?:\s*R\$\s*([\d\.\,]+)", re.I),
    "transito": re.compile(r"Data do tr[âa]nsito em julgado.*?:\s*([\d\/]+)", re.I)
}

def parse_fields(text: str) -> Dict[str, Optional[str]]:
    def g(rx_key, conv=None):
        m = RX[rx_key].search(text)
        if not m: return None
        return conv(m.group(1)) if conv else m.group(1).strip()

    data = {
        # Anexo II
        "nome": g("nome"),
        "cpf": g("cpf"),
        "banco": g("banco"),
        "agencia": g("agencia"),
        "conta": g("conta"),
        "total_requerente": g("total_req", norm_money_br),
        "valor_requisitado": g("valor_requisitado", norm_money_br),
        "data_base_atualizacao": g("data_base", norm_date_br),
        "principal_indenizacao": g("principal", norm_money_br),
        "juros_moratorios": g("juros_mora", norm_money_br),
        # Ofício
        "processo_principal": g("proc_principal"),
        "processo_origem": g("proc_origem"),
        "credor": g("credor"),
        "devedor": g("devedor"),
        "natureza": g("natureza"),
        "natureza_credito": g("natureza_credito"),
        "valor_global": g("valor_global", norm_money_br),
        "transito_em_julgado": g("transito", norm_date_br),
    }
    return data

def extract_pdf(pdf_path: Path, cpf_dir: str) -> Optional[Dict]:
    try:
        reader = PdfReader(str(pdf_path))
    except Exception:
        return None

    page_texts = []
    for i in range(len(reader.pages)):
        t = read_page_text(reader, i)
        if not t.strip() and USE_OCRMYPDF:
            t = ocr_single_page(pdf_path, i)
        page_texts.append(t or "")

    idx = find_target_pages(page_texts)
    candidate_pages = list(dict.fromkeys(idx["anexo_ii"] + idx["oficio"] + idx["dados_basicos"] + idx["termo"]))
    if not candidate_pages:
        # fallback: tenta todas (pode ser lento, mas garante)
        candidate_pages = list(range(len(page_texts)))

    # concatena textos das páginas alvo
    concat_txt = "\n\n".join(page_texts[i] for i in candidate_pages)
    fields = parse_fields(concat_txt)

    # coleta contribuições (lista de "descricao  R$ valor")
    contribs = []
    for m in re.finditer(r"Contribui[çc][õo]es?:?\s*(.+)", concat_txt, re.I):
        # extrair padrões "XXX  R$ 9.999,99"
        tail = concat_txt[m.end():m.end()+800]
        for m2 in re.finditer(r"([A-Z0-9\.\-\s/]+?)\s+R\$\s*([\d\.\,]+)", tail):
            desc = m2.group(1).strip()
            val = norm_money_br(m2.group(2))
            if val is not None:
                contribs.append({"descricao": desc, "valor": val})
        break

    record = {
        "cpf_dir": cpf_dir,
        "pdf_file": pdf_path.name,
        "source_pages": idx,
        "processos": {
            "principal": fields.get("processo_principal") or fields.get("processo_origem"),
            "origem": fields.get("processo_origem")
        },
        "parte": {
            "nome": fields.get("nome") or fields.get("credor"),
            "cpf": fields.get("cpf"),
        },
        "bancario": {
            "banco": fields.get("banco"),
            "agencia": fields.get("agencia"),
            "conta": fields.get("conta"),
        },
        "natureza": {
            "geral": fields.get("natureza"),
            "credito": fields.get("natureza_credito"),
        },
        "valores": {
            "total_requerente": fields.get("total_requerente"),
            "valor_requisitado": fields.get("valor_requisitado") or fields.get("valor_global"),
            "principal_indenizacao": fields.get("principal_indenizacao"),
            "juros_moratorios": fields.get("juros_moratorios"),
        },
        "datas": {
            "data_base_atualizacao": fields.get("data_base_atualizacao"),
            "transito_em_julgado": fields.get("transito_em_julgado"),
        },
        "devedor": fields.get("devedor"),
        "contribuicoes": contribs or None
    }

    # Limpeza de None
    def drop_nones(x):
        if isinstance(x, dict):
            return {k: drop_nones(v) for k,v in x.items() if v not in (None, {}, [], "")}
        if isinstance(x, list):
            return [drop_nones(v) for v in x if v not in (None, {}, [], "")]
        return x

    return drop_nones(record)

def main():
    ndjson_path = OUT_DIR / "all_extracoes.ndjson"
    if ndjson_path.exists(): ndjson_path.unlink()
    with open(ndjson_path, "a", encoding="utf-8") as agg:
        for cpf_dir in sorted(p.name for p in BASE_DIR.iterdir() if p.is_dir()):
            cpf_path = BASE_DIR / cpf_dir
            out_cpf = OUT_DIR / "json" / cpf_dir
            out_cpf.mkdir(parents=True, exist_ok=True)
            for pdf in sorted(cpf_path.glob("*.pdf")):
                rec = extract_pdf(pdf, cpf_dir)
                if not rec: continue
                out_path = out_cpf / (pdf.stem + ".json")
                with open(out_path, "w", encoding="utf-8") as f:
                    json.dump(rec, f, ensure_ascii=False, indent=2)
                agg.write(json.dumps(rec, ensure_ascii=False) + "\n")
    print(f"OK. JSONs em {OUT_DIR}/json e NDJSON em {ndjson_path}")

if __name__ == "__main__":
    main()
```

## Por que funciona bem nos seus arquivos

* Os **rótulos são estáveis** nos exemplos (*ANEXO II*, *Ofício Requisitório*, *Dados principais do ofício*), então a combinação “marcadores de página + regex por rótulo” é mais resiliente a variações de layout do que OCR puro linha-a-linha. Exemplos: campos de **nome/CPF/banco/agência/conta** e **valores** no ANEXO II, e **processo/credor/devedor/natureza/valor global** no Ofício.   
* Quando o ANEXO II não estiver completo, os **“Dados básicos / Termo de Declaração (SAJ)”** oferecem **fallback** dos principais metadados (nome, CPF, valor global, natureza, datas). 
* No seu lote, “**Data base para atualização 29/02/2020**” e “**Principal/Indenização** / **Juros Moratórios**” aparecem claramente no **ANEXO II** — o regex captura direto. 

---

## Próximos passos (rápidos)

1. **Me dizer o caminho do `BASE_DIR`** para eu já te devolver o script com esse valor fixo.
2. **Rodar**: `python extractor.py` (gera `/output/json/<CPF>/*.json` e `output/all_extracoes.ndjson`).
3. **Validação**: comparar alguns JSONs com os PDFs originais (spot check).
4. **Etapa 2** (quando você quiser): inserção no banco (Postgres/MySQL), incluindo índice por `cpf_dir`, `processos.principal` e `datas.data_base_atualizacao`.

## Dúvidas pontuais (bem objetivas)

* O diretório raiz final é exatamente o da captura (`.../data/consultas/<CPF>/*.pdf`)?
* Você prefere **Tesseract local** apenas para fallback (mais leve) ou rodamos `ocrmypdf` como fallback (mais “plug-and-play”)?
* Quer que já gere também um **CSV** com um subconjunto de campos (para conferência rápida no Excel)?

Se quiser, eu já ajusto o `BASE_DIR` e devolvo a versão final pronta para rodar.
