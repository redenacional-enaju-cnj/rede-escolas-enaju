# Rede ENAJU — persistência, CSV e integração com SharePoint CNJ

**Estado:** desenho técnico e estágio intermediário implantado em 19/11/2026. **Não** constitui integração ativa com SharePoint CNJ.

## 1. O que já está ativo no repositório

- Diretório público: `dados/escolas-diagnostico-2025.json` (110 unidades).
- Dicionário normativo operacional: `dados/itens-checklist-2027.json` (13 subitens de 2027).
- Projeção tabular inicial: `dados/checklist-escolas-2027.csv` (110 × 13 = 1.430 registros).
- Metadados da projeção: `dados/checklist-escolas-2027-metadata.json`.
- Exportador: `scripts/exportar_checklists_csv.py`.
- Automação: `.github/workflows/exportar-checklists-2027.yml` (evento de Issue, execução manual e atualização diária).
- Entrada de respostas atual: formulário `checklist-escolas-2027.html` → abertura de GitHub Issue, com confirmação pela escola.

**Limite:** o clique num status não escreve diretamente no CSV nem no SharePoint. É preciso publicar a autodeclaração no GitHub. O CSV é **cópia de leitura**, regenerada de forma automatizada a partir das Issues, e não uma base transacional.

### Fontes e rastreabilidade

Cada linha tem chave composta `id_unidade + id_requisito`, artigo, classificação de aplicabilidade, situação, datas, URL da declaração, origem e `validacao=nao_homologado`.
Até que exista declaração, a situação é `nao_informado`; para itens excluídos do escopo inferido, `fora_escopo_inferido`. Não se interpreta ausência de resposta como descumprimento.

## 2. Arquitetura institucional recomendada

`Portal público (GitHub Pages)`
→ `formulário autenticado/API segura`
→ `Microsoft Lists no SharePoint CNJ (fonte da verdade)`
→ `Power Automate: histórico, notificações, revisão pela ENAJU`
→ `CSV/Excel/Power BI e painel público com dados permitidos`.

Um site estático não deve receber credenciais ou tokens Microsoft Graph em JavaScript público. A API de gravação, permissões e trilha de auditoria devem permanecer em camada segura com autenticação.

### Listas sugeridas

1. **ENAJU_Escolas** — id_unidade, nome institucional, sigla_órgão, ramo, UF, natureza, status do cadastro.
2. **ENAJU_Requisitos_2027** — id_requisito, artigo, título, público, incidência por segmento, documentação, janela.
3. **ENAJU_Autodeclaracoes_2027** — chave `id_unidade|id_requisito` única, escola, requisito, situação, data, justificativa institucional opcional, usuário autorizado, versão, status da revisão ENAJU, data de revisão.
4. **ENAJU_Historico_Declaracoes** — alterações imutáveis: chave, situação anterior/nova, data e origem do registro.
5. **ENAJU_Cursos_Compartilhados** — id_curso, escola, título, horas, modalidade, URL oficial, disponibilidade, situação da revisão ENAJU.
6. **ENAJU_Curso_Requisito** — id_curso, id_requisito, tipo de aderência e parecer técnico; N:N para vincular a mesma formação a vários itens.

### Situações distintas

- **Situação da escola:** `cumprido`, `nao_cumprido`, `andamento`, `nao_informado`, `nao_aplicavel`.
- **Revisão ENAJU:** `nao_analisado`, `pendente_ajuste`, `pre_analisado`, `nao_confirmado`.
- **Reconhecimento do prêmio:** só pode decorrer de procedimento do CNJ/DPJ e da Comissão Avaliadora; não é calculado pelo protótipo.

## 3. Como ligar ao SharePoint do CNJ

Pré-requisito: conta corporativa do CNJ com acesso autorizado ao site, lista e ferramenta de fluxo; confirmação de política de compartilhamento com as escolas de outros tribunais. A conexão Microsoft disponível ao assistente em 19/11/2026 corresponde a **OneDrive pessoal** e não concede acesso ao SharePoint corporativo.

Passos de implantação:

1. A equipe CNJ define o site SharePoint, cria as listas com os campos anteriores e identifica os gestores ENAJU/DPJ.
2. Estabelece forma de acesso das escolas (conta federada, convite B2B ou outro mecanismo autorizado); não confiar apenas em campo editável que indique o tribunal.
3. Registra uma API de gravação protegida em serviço controlado institucionalmente, ou usa formulário Microsoft associado a Power Automate; regras de autenticação/limitações de licença serão validadas com o DTI.
4. Ao salvar, o serviço faz upsert por `id_unidade|id_requisito`, gera histórico e devolve confirmação **somente depois** da gravação bem-sucedida.
5. O painel consulta dados com permissões apropriadas; disponibiliza ao público exclusivamente agregados ou campos expressamente autorizados.
6. Gera CSV de exportação periódica, incluindo o ID da escola, ID do item, status, datas, origem e revisão.

### Alternativa de implantação mais rápida

Se a infraestrutura CNJ não estiver disponível, é possível hospedar provisoriamente a base em **Google Sheets + Apps Script**, com acesso administrado pela ENAJU. A URL de um aplicativo de Fábio foi identificada, mas não se obteve acesso à estrutura da API para gravar na mesma planilha. Portanto, não deve ser reutilizada como endpoint de escrita sem confirmação explícita do contrato de dados e das permissões.

## 4. Governança e privacidade

- Não divulgar contatos, identificação pessoal de respondentes ou documentos institucionais no repositório público.
- Nenhum servidor de formulário deve permitir modificar declarações de outras escolas sem autorização.
- Um mesmo tribunal pode ter várias escolas; status escolar e pontuação do tribunal não são equivalentes.
- Não importar status do Diagnóstico 2025/2026 como cumprimento do prêmio de 2027.
- O registro é autodeclaratório e serve a planejamento, monitoramento e eventual pré-análise pactuada com DPJ.
- Usar controle de acesso, logs, limites de requisição, backups, política de retenção e plano de correção de incidentes antes de processamento institucional.

## 5. Documentação oficial

- Microsoft Graph: https://learn.microsoft.com/pt-br/graph/api/listitem-create?view=graph-rest-1.0
- SharePoint + Power Automate: https://learn.microsoft.com/en-us/power-automate/sharepoint-overview
- Forms + Power Automate: https://learn.microsoft.com/en-us/power-automate/forms/overview
