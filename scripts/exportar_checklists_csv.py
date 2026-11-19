#!/usr/bin/env python3
"""Exporta autodeclarações públicas do checklist ENAJU em CSV auditável.

Fonte de verdade atual: GitHub Issues estruturadas do portal Rede ENAJU.
Este arquivo CSV é uma projeção do estado das declarações, não um banco editável.
Os registros são públicos e NÃO equivalem à validação/atribuição de pontos do CNJ.
Executar no repositório: python scripts/exportar_checklists_csv.py
"""
import csv
import json
import os
import re
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ROSTER = ROOT / "dados" / "escolas-diagnostico-2025.json"
CRITERIA = ROOT / "dados" / "itens-checklist-2027.json"
OUTPUT = ROOT / "dados" / "checklist-escolas-2027.csv"
META = ROOT / "dados" / "checklist-escolas-2027-metadata.json"
REPO = os.environ.get("GITHUB_REPOSITORY", "redenacional-enaju-cnj/rede-escolas-enaju")
TOKEN = os.environ.get("GITHUB_TOKEN", "").strip()
ALLOWED = {"cumprido", "nao_cumprido", "andamento", "nao_informado", "nao_aplicavel"}
ISSUE_BLOCK = re.compile(r"```json\s*([\s\S]*?)\s*```")
FIELDS = ["id_unidade", "escola", "orgao", "uf", "ramo", "id_requisito",
          "artigo", "grupo", "descricao_requisito", "aplicabilidade",
          "situacao", "data_declaracao", "data_atualizacao", "issue_url",
          "origem", "validacao"]

def safe_csv(value):
    """Desabilita interpretação de fórmulas em Excel/planilhas."""
    val = str(value if value is not None else "")
    if val and val.lstrip().startswith(("=", "+", "-", "@", "\t", "\r")):
        return "'" + val
    return val

def tribunal_type(sigla):
    if sigla.startswith("TRF"): return "TRF"
    if sigla.startswith("TRT"): return "TRT"
    if sigla.startswith("TRE"): return "TRE"
    if sigla.startswith("TJM"): return "TJM"
    if sigla.startswith("TJ"): return "TJ"
    if sigla in ("TST", "STJ", "STM", "TSE"): return "SUPER"
    return "OUTRO"

def applicable(school, item):
    tipo = tribunal_type(school.get("orgao", ""))
    return tipo != "OUTRO" and ("ALL" in item["ramo"] or tipo in item["ramo"])

def fetch_issues():
    if not TOKEN:
        raise RuntimeError("GITHUB_TOKEN ausente: exportação live não autorizada")
    result = []
    for page in range(1, 21):
        url = f"https://api.github.com/repos/{REPO}/issues?state=all&per_page=100&page={page}"
        req = urllib.request.Request(url, headers={
            "Authorization": f"Bearer {TOKEN}",
            "Accept": "application/vnd.github+json",
            "User-Agent": "Rede-ENAJU-CSV-Exporter",
            "X-GitHub-Api-Version": "2022-11-28"
        })
        with urllib.request.urlopen(req, timeout=30) as response:
            batch = json.load(response)
        result.extend(x for x in batch if "pull_request" not in x)
        if len(batch) < 100: break
    return result

def parse_declaration(issue, schools, item_ids):
    match = ISSUE_BLOCK.search(issue.get("body") or "")
    if not match:
        return None
    try:
        data = json.loads(match.group(1))
    except (ValueError, TypeError):
        return None
    if not isinstance(data, dict) or data.get("type") != "enaju_school_checklist_2027" or data.get("version") != 1:
        return None
    uid = data.get("school_id")
    answers = data.get("items")
    if uid not in schools or not isinstance(answers, dict):
        return None
    if any(key not in item_ids or status not in ALLOWED for key, status in answers.items()):
        return None
    return {"id_unidade": uid, "items": answers,
            "date": issue.get("created_at") or "",
            "updated_at": issue.get("updated_at") or "",
            "url": issue.get("html_url") or "",
            "sequence": issue.get("number", 0)}

def build_export():
    roster = json.loads(ROSTER.read_text(encoding="utf-8"))
    school_list = roster["escolas"]
    items = json.loads(CRITERIA.read_text(encoding="utf-8"))["itens"]
    schools = {s["id"]: s for s in school_list}
    item_ids = {c["id"] for c in items}
    issues = fetch_issues()
    parsed = [p for issue in issues if (p := parse_declaration(issue, schools, item_ids))]
    parsed.sort(key=lambda p: (p["date"], p["sequence"]))
    latest = {p["id_unidade"]: p for p in parsed}
    rows = []
    for school in sorted(school_list, key=lambda s: (s["uf"], s["orgao"], s["nome"])):
        rec = latest.get(school["id"])
        for item in items:
            applies = applicable(school, item)
            # Itens fora do escopo inferido nunca são apresentados como 'não cumpridos'.
            status = (rec["items"].get(item["id"], "nao_informado") if rec and applies
                      else "fora_escopo_inferido" if not applies else "nao_informado")
            rows.append({
                "id_unidade": school["id"], "escola": school["nome"], "orgao": school["orgao"],
                "uf": school["uf"], "ramo": school["ramo"], "id_requisito": item["id"],
                "artigo": item["art"], "grupo": item["grupo"],
                "descricao_requisito": item["titulo"],
                "aplicabilidade": "aplicavel_inferido" if applies else "fora_escopo_inferido",
                "situacao": status, "data_declaracao": rec["date"] if rec else "",
                "data_atualizacao": rec["updated_at"] if rec else "",
                "issue_url": rec["url"] if rec else "",
                "origem": "github_issue_autodeclaracao" if rec else "diretorio_diagnostico",
                "validacao": "nao_homologado",
            })
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    with OUTPUT.open("w", newline="", encoding="utf-8-sig") as fp:
        writer = csv.DictWriter(fp, fieldnames=FIELDS, delimiter=";")
        writer.writeheader()
        writer.writerows({key: safe_csv(value) for key, value in row.items()} for row in rows)
    # Metadados não contêm identificadores pessoais.
    summary = {"atualizado_em_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
               "origem": "GitHub Issues públicas + cadastro público ENAJU",
               "natureza": "autodeclaracao_nao_homologada",
               "unidades_catalogadas": len(school_list),
               "subitens_cadastrados": len(items), "linhas_csv": len(rows),
               "unidades_com_declaracao": len(latest),
               "linhas_declaradas_cumpridas": sum(x["situacao"] == "cumprido" for x in rows),
               "linhas_declaradas_nao_cumpridas": sum(x["situacao"] == "nao_cumprido" for x in rows),
               "observacao": "Ausência de declaração não significa descumprimento. A classificação de incidência é preliminar."}
    META.write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(summary, ensure_ascii=False))

if __name__ == "__main__":
    build_export()
