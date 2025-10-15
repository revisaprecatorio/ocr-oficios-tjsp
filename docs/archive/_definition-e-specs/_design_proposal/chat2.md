perfeito! abaixo vai um pacote “pronto-pra-rodar” no **Windows Server**: instalações rápidas, e um **script único** que varre `data\consultas\<CPF>\*.pdf`, extrai os campos do **Ofício Requisitório / ANEXO II**, salva **JSON por PDF**, **NDJSON agregado** e um **CSV resumido** para conferência.

---

# Passo 0 — Instalação no Windows Server

Abra **PowerShell (Admin)** e rode:

```powershell
# Chocolatey (se ainda não tiver)
Set-ExecutionPolicy Bypass -Scope Process -Force
[System.Net.ServicePointManager]::SecurityProtocol = [System.Net.SecurityProtocolType]::Tls12
iex ((New-Object System.Net.WebClient).DownloadString('https://chocolatey.org/install.ps1'))

# Tesseract OCR e Poppler (necessário para converter PDF -> imagem quando precisar de OCR)
choco install -y tesseract
choco install -y poppler

# (Opcional) Pacote de idioma PT-BR do Tesseract
choco install -y tesseract-ocr-por
```

Depois, crie e ative um venv (opcional, mas recomendado) e instale as libs Python:

```powershell
python -m venv venv
.\venv\Scripts\Activate.ps1
pip install --upgrade pip
pip install PyPDF2 pdf2image pillow pytesseract
```

> Observação: o **pdf2image** precisa do `poppler`. Acima já instalamos; no script abaixo eu mostro como apontar para o caminho padrão do Poppler do Chocolatey.

---

# Passo 1 — Script de extração (JSON + NDJSON + CSV)

Salve como `extract_oficio_tjsp.py` e ajuste o `BASE_DIR` se necessário (eu deixei um caminho típico no Windows):

```python
# -*- coding: utf-8 -*-
"""
Extractor TJSP - Ofício Requisitório / ANEXO II
- Varre data\consultas\<CPF>\*.pdf
- Extrai campos via texto nativo; se a página não tiver texto, usa OCR (pdf2image + pytesseract)
- Gera:
  - JSON por PDF:        output/json/<CPF>/<arquivo>.json
  - NDJSON agregado:     output/all_extracoes.ndjson
  - CSV resumido:        output/extracoes_subset.csv
"""

from pathlib import Path
import os, re, json, csv, tempfile
from typing import Dict, List, Optional
from datetime import datetime

import pytesseract
from PyPDF2 import PdfReader
from pdf2image import convert_from_path
from PIL import Image

# =========================
# CONFIG
# =========================
# >>> AJUSTE AQUI CONFORME SEU AMBIENTE <<<
BASE_DIR = Path(r"C:\Users\Administrator\Documents\data\consultas")  # raiz com subpastas de CPFs
OUT_DIR  = Path("./output")

# Caminho do Poppler (instalado via choco). Normalmente:
# C:\ProgramData\chocolatey\lib\poppler\tools\poppler-*\Library\bin
# Vamos tentar detectar automaticamente varrendo a pasta.
DEFAULT_POPPLER_ROOT = Path(r"C:\ProgramData\chocolatey\lib\poppler")
POPPLER_BIN = None
if DEFAULT_POPPLER_ROOT.exists():
    # escolhe a subpasta mais recente
    subs = sorted(DEFAULT_POPPLER_ROOT.glob("**/Library/bin"), key=lambda p: len(str(p)))
    if subs:
        POPPLER_BIN = str(subs[-1])

# Tesseract (via choco) costuma estar no PATH; se não, ajuste:
# pytesseract.pytesseract.tesseract_cmd = r"C:\Program Files\Tesseract-OCR\tesseract.exe"

OUT_DIR.mkdir(parents=True, exist_ok=True)
(OUT_DIR / "json").mkdir(exist_ok=True)

# =========================
# Utilitários
# =========================
def norm_money_br(val: str) -> Optional[float]:
    if not val: return None
    s = val.upper().replace("R$", "").replace(" ", "")
    s = s.replace(".", "").replace(",", ".")
    try:
        return float(s)
    except Exception:
        return None

def norm_date_br(d: str) -> Optional[str]:
    d = d.strip()
    for fmt in ("%d/%m/%Y", "%d/%m/%y"):
        try:
            return datetime.strptime(d, fmt).date().isoformat()
        except Exception:
            pass
    return None

def read_page_text(reader: PdfReader, page_index: int) -> str:
    try:
        t = reader.pages[page_index].extract_text()
        return t or ""
    except Exception:
        return ""

def ocr_page_to_text(pdf_path: Path, page_index: int) -> str:
    """OCR de UMA página: converte a página em imagem e aplica Tesseract."""
    try:
        images = convert_from_path(
            pdf_path.as_posix(),
            first_page=page_index + 1,
            last_page=page_index + 1,
            poppler_path=POPPLER_BIN
        )
        if not images: 
            return ""
        img: Image.Image = images[0]
        # PT + EN ajuda no vocabulário
        return pytesseract.image_to_string(img, lang="por+eng")
    except Exception:
        return ""

PAGE_MARKERS = [
    r"ANEXO\s+II",
    r"OF[ÍI]CIO\s+REQUISIT[ÓO]RIO",
    r"DADOS\s+PRINCIPAIS\s+DO\s+OF[ÍI]CIO\s+REQUISIT[ÓO]RIO",
    r"TERMO\s+DE\s+DECLARA[ÇC][ÃA]O"
]
PAGE_MARKERS = [re.compile(p, re.I) for p in PAGE_MARKERS]

def find_target_pages(all_texts: List[str]) -> Dict[str, List[int]]:
    idx = {"anexo_ii": [], "oficio": [], "dados_basicos": [], "termo": []}
    for i, t in enumerate(all_texts):
        if re.search(PAGE_MARKERS[0], t): idx["anexo_ii"].append(i)
        if re.search(PAGE_MARKERS[1], t): idx["oficio"].append(i)
        if re.search(PAGE_MARKERS[2], t): idx["dados_basicos"].append(i)
        if re.search(PAGE_MARKERS[3], t): idx["termo"].append(i)
    return idx

RX = {
    # ANEXO II
    "nome": re.compile(r"Nome:\s*(.+)"),
    "cpf": re.compile(r"CPF/CNPJ/RNE:\s*([\d\.\-\/]+)"),
    "banco": re.compile(r"Banco:\s*(\d+)"),
    "agencia": re.compile(r"Ag[êe]ncia:\s*([\d\-]+)"),
    "conta": re.compile(r"Conta:\s*([\d\.\-]+)"),
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
    "transito": re.compile(r"Data do tr[âa]nsito em julgado.*?:\s*([\d\/]+)", re.I),
}

def parse_fields(text: str) -> Dict[str, Optional[str]]:
    def g(k, conv=None):
        m = RX[k].search(text)
        if not m: return None
        return conv(m.group(1)) if conv else m.group(1).strip()

    return {
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

        "processo_principal": g("proc_principal"),
        "processo_origem": g("proc_origem"),
        "credor": g("credor"),
        "devedor": g("devedor"),
        "natureza": g("natureza"),
        "natureza_credito": g("natureza_credito"),
        "valor_global": g("valor_global", norm_money_br),
        "transito_em_julgado": g("transito", norm_date_br),
    }

def drop_nones(x):
    if isinstance(x, dict):
        return {k: drop_nones(v) for k, v in x.items() if v not in (None, "", [], {})}
    if isinstance(x, list):
        return [drop_nones(v) for v in x if v not in (None, "", [], {})]
    return x

def extract_pdf(pdf_path: Path, cpf_dir: str) -> Optional[Dict]:
    try:
        reader = PdfReader(str(pdf_path))
    except Exception:
        return None

    # 1) texto nativo
    texts = [read_page_text(reader, i) for i in range(len(reader.pages))]

    # 2) se a página está “vazia”, faz OCR nela (só nas vazias)
    for i, t in enumerate(texts):
        if not t.strip():
            texts[i] = ocr_page_to_text(pdf_path, i)

    idx = find_target_pages(texts)
    cand = list(dict.fromkeys(idx["anexo_ii"] + idx["oficio"] + idx["dados_basicos"] + idx["termo"]))
    if not cand:
        cand = list(range(len(texts)))

    concat = "\n\n".join(texts[i] for i in cand)
    f = parse_fields(concat)

    # contribuições (se listadas)
    contribs = []
    m = re.search(r"Contribui[çc][õo]es?:?(.*)", concat, re.I | re.S)
    if m:
        tail = m.group(1)[:800]
        for m2 in re.finditer(r"([A-Z0-9\.\-\s/]+?)\s+R\$\s*([\d\.\,]+)", tail):
            desc = m2.group(1).strip()
            val = norm_money_br(m2.group(2))
            if val is not None:
                contribs.append({"descricao": desc, "valor": val})

    rec = {
        "cpf_dir": cpf_dir,
        "pdf_file": pdf_path.name,
        "source_pages": idx,
        "processos": {
            "principal": f.get("processo_principal") or f.get("processo_origem"),
            "origem": f.get("processo_origem")
        },
        "parte": {
            "nome": f.get("nome") or f.get("credor"),
            "cpf": f.get("cpf"),
        },
        "bancario": {
            "banco": f.get("banco"),
            "agencia": f.get("agencia"),
            "conta": f.get("conta"),
        },
        "natureza": {
            "geral": f.get("natureza"),
            "credito": f.get("natureza_credito"),
        },
        "valores": {
            "total_requerente": f.get("total_requerente"),
            "valor_requisitado": f.get("valor_requisitado") or f.get("valor_global"),
            "principal_indenizacao": f.get("principal_indenizacao"),
            "juros_moratorios": f.get("juros_moratorios"),
        },
        "datas": {
            "data_base_atualizacao": f.get("data_base_atualizacao"),
            "transito_em_julgado": f.get("transito_em_julgado"),
        },
        "devedor": f.get("devedor"),
        "contribuicoes": contribs or None
    }
    return drop_nones(rec)

def main():
    ndjson_path = OUT_DIR / "all_extracoes.ndjson"
    csv_path = OUT_DIR / "extracoes_subset.csv"

    # zera arquivos se já existirem
    if ndjson_path.exists(): ndjson_path.unlink()
    if csv_path.exists(): csv_path.unlink()

    subset_fields = [
        "cpf_dir","pdf_file","parte.nome","parte.cpf",
        "processos.principal","devedor",
        "valores.total_requerente","valores.valor_requisitado","valores.principal_indenizacao","valores.juros_moratorios",
        "datas.data_base_atualizacao"
    ]

    # CSV header
    with open(csv_path, "w", newline="", encoding="utf-8") as cf:
        cw = csv.writer(cf, delimiter=";")
        cw.writerow(subset_fields)

    with open(ndjson_path, "a", encoding="utf-8") as agg:
        for cpf_dir in sorted(p.name for p in BASE_DIR.iterdir() if p.is_dir()):
            cpf_path = BASE_DIR / cpf_dir
            (OUT_DIR / "json" / cpf_dir).mkdir(parents=True, exist_ok=True)
            for pdf in sorted(cpf_path.glob("*.pdf")):
                rec = extract_pdf(pdf, cpf_dir)
                if not rec: 
                    continue

                # salva JSON por PDF
                out_path = OUT_DIR / "json" / cpf_dir / (pdf.stem + ".json")
                with open(out_path, "w", encoding="utf-8") as jf:
                    json.dump(rec, jf, ensure_ascii=False, indent=2)

                # agrega NDJSON
                agg.write(json.dumps(rec, ensure_ascii=False) + "\n")

                # escreve linha no CSV resumido
                def get(d, path, default=""):
                    cur = d
                    for k in path.split("."):
                        if isinstance(cur, dict) and k in cur:
                            cur = cur[k]
                        else:
                            return default
                    return cur if cur is not None else default

                row = [
                    get(rec,"cpf_dir"),
                    get(rec,"pdf_file"),
                    get(rec,"parte.nome"),
                    get(rec,"parte.cpf"),
                    get(rec,"processos.principal"),
                    get(rec,"devedor"),
                    get(rec,"valores.total_requerente"),
                    get(rec,"valores.valor_requisitado"),
                    get(rec,"valores.principal_indenizacao"),
                    get(rec,"valores.juros_moratorios"),
                    get(rec,"datas.data_base_atualizacao"),
                ]
                with open(csv_path, "a", newline="", encoding="utf-8") as cf:
                    csv.writer(cf, delimiter=";").writerow(row)

    print(f"OK ✅")
    print(f"- JSONs: {OUT_DIR}\\json\\<CPF>\\*.json")
    print(f"- NDJSON: {ndjson_path}")
    print(f"- CSV:    {csv_path}")

if __name__ == "__main__":
    main()
```

### O que sai no CSV (exemplo de colunas)

* `cpf_dir`, `pdf_file`
* `parte.nome`, `parte.cpf`
* `processos.principal`, `devedor`
* `valores.total_requerente`, `valores.valor_requisitado`, `valores.principal_indenizacao`, `valores.juros_moratorios`
* `datas.data_base_atualizacao`

Delimitador `;` para abrir no Excel/LibreOffice sem bagunçar números com vírgula.

---

## Como rodar

```powershell
.\venv\Scripts\Activate.ps1   # se estiver usando venv
python .\extract_oficio_tjsp.py
```

Saídas:

* JSON por PDF: `output\json\<CPF>\*.json`
* NDJSON agregado: `output\all_extracoes.ndjson`
* **CSV de conferência**: `output\extracoes_subset.csv`

---

## Observações finais

* O script só faz **OCR nas páginas sem texto**, o que mantém o desempenho bom mesmo em lotes grandes.
* Se algum layout fugir dos rótulos, a gente inclui mais *patterns* de página e *regex*—o arcabouço já está preparado.
* Assim que você rodar o primeiro lote, me diga se quer que eu **ajuste os campos do CSV** (trocar/adição de colunas) ou se já partimos para a **Etapa 2 (inserção no banco)**.
