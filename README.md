# DBCrafter

Aplicação web para converter **CSV, JSON, XLSX e XLS** em scripts `INSERT INTO`, com saídas para **SQLite, PostgreSQL, MySQL e Oracle 19c+**.

Os arquivos e o SQL ficam em memória durante a requisição. A aplicação **não executa SQL, não cria tabelas e não grava os dados em um banco local**. Cada download é isolado dos demais usuários.

## Executar localmente

Requer Python 3.12. Use um ambiente virtual:

```bash
python -m venv .venv
source .venv/bin/activate
pip install --require-hashes -r requirements.txt
python -m src.main
```

No Windows, ative com `.venv\Scripts\activate`. Abra <http://127.0.0.1:5000>. O comando antigo `python src/main.py` também funciona. O servidor local fica sem debug e escuta apenas em localhost; não é o comando de produção.

## Docker

```bash
docker compose up --build -d
docker compose down
```

Abra <http://127.0.0.1:5000>. A configuração inclui usuário sem privilégios, sistema de arquivos somente leitura, limites de 512 MiB de memória/1 CPU/64 processos e Gunicorn com timeout de 30 segundos. Não há volume de dados nem montagem do código do host.

Para construir a imagem separadamente:

```bash
docker build -t dbcrafter .
docker run --rm -p 127.0.0.1:5000:5000 --read-only --tmpfs /tmp:size=16m --memory=512m --cpus=1 --pids-limit=64 --cap-drop=ALL --security-opt=no-new-privileges dbcrafter
```

A tag Python recebe correções; para reconstruir a mesma imagem byte a byte, registre também o digest da imagem base usada no seu ambiente.

## Produção / Render

Instalação: `pip install --require-hashes -r requirements.txt`.

Comando de inicialização, já definido no `Procfile`:

```bash
gunicorn --config gunicorn.conf.py src.wsgi:app
```

O Gunicorn usa `PORT` (padrão 5000) e um worker síncrono. No Render, ajuste o **Start Command** existente: mudar o Procfile não substitui automaticamente um comando configurado no painel. Configure o health check em `/healthz` e Python 3.12, ou use o Dockerfile.

Termine HTTPS no proxy/plataforma e aplique limites de conexão, corpo e taxa também na borda. A aplicação sozinha não protege contra ataques volumétricos. Gunicorn funciona em Linux/WSL; para produção em Windows, use o contêiner.

### Configurações de implantação

| Variável | Padrão | Uso |
|---|---|---|
| `PORT` | `5000` | Porta HTTP do Gunicorn |
| `WEB_CONCURRENCY` | `1` | Workers; valores maiores exigem armazenamento compartilhado para o limitador |
| `DBCRAFTER_RATELIMIT_STORAGE_URI` | `memory://` | Opcionalmente `redis://...` / `rediss://...` para vários workers ou réplicas |
| `DBCRAFTER_UPLOAD_RATE_LIMIT` | `10 per minute` | Tentativas de conversão por IP, incluindo inválidas |
| `DBCRAFTER_GLOBAL_RATE_LIMIT` | `60 per minute` | Tentativas totais de conversão por instância/armazenamento compartilhado |
| `DBCRAFTER_TRUSTED_PROXY_HOPS` | `0` | Quantidade exata de proxies confiáveis na frente da aplicação |
| `DBCRAFTER_TRUSTED_HOSTS` | não definido | Lista JSON dos hosts aceitos, por exemplo `["dbcrafter.example.com","127.0.0.1"]` |

**Não habilite confiança no proxy sem confirmar a topologia.** O servidor precisa estar inacessível diretamente e o proxy deve sobrescrever os cabeçalhos encaminhados. Por padrão, `X-Forwarded-For` não permite contornar os limites. Sem essa configuração, clientes atrás do mesmo proxy podem compartilhar a mesma cota.

O armazenamento em memória perde os contadores ao reiniciar e é por processo. Para mais de uma réplica, use Redis compartilhado ou limites globais na borda; Redis armazena apenas contadores do limitador, nunca os uploads. Não publique sua URI com credenciais no repositório.

## Conversão e tipos

1. Envie um arquivo e informe uma tabela ou `schema.tabela` já existente.
2. Escolha o banco de destino e, opcionalmente, a quantidade de linhas.
3. Ajuste os tipos por coluna, se necessário, e baixe `inserts.sql`.

### Entrada

- **CSV:** UTF-8 (BOM aceito); separador explícito: vírgula, ponto e vírgula ou tabulação. Leitura incremental de linhas, sem inferência de números/datas. `00123`, `NA` e `NULL` continuam sendo textos. Campo vazio é `''`; apenas o marcador escolhido (padrão `\N`) vira `NULL`.
- **JSON:** array não vazio de objetos com as mesmas chaves; ordem das chaves pode variar. Números decimais são lidos com `Decimal`, sem passar por float. `null` e booleanos mantêm seus tipos. Chaves duplicadas, dados aninhados, NaN e Infinity são rejeitados. O JSON é carregado integralmente dentro do limite de 5 MiB.
- **XLSX:** primeira aba, primeira linha como cabeçalho. Leitura em modo read-only; fórmulas, erros, macros e arquivos que excedem os limites descompactados são rejeitados. XML usa `defusedxml`.
- **XLS:** primeira aba via `xlrd`; lê os valores salvos, inclusive resultados em cache de fórmulas. Não recalcula nem executa fórmulas ou macros. Exporte apenas valores se precisar eliminar resultados desatualizados.

Excel armazena números com precisão limitada. Nenhuma biblioteca recupera dígitos já arredondados no arquivo. Para identificadores longos ou decimais exatos, use células de texto ou CSV/JSON e um tipo explícito.

### Cabeçalhos e tipos explícitos

Cabeçalhos viram minúsculas ASCII, acentos são removidos, pontuação/espaços viram `_`, e nomes começando com número recebem `c_`. Nomes vazios, acima de 63 caracteres ou colidentes são rejeitados. Exemplo: `Preço Unitário` → `preco_unitario`. Não há renomeação silenciosa de duplicatas.

O campo opcional **Tipos por coluna** usa os nomes normalizados:

```json
{"id":"integer","preco_unitario":"decimal","ativo":"boolean","data":"date","instante":"datetime"}
```

Tipos: `text`, `integer`, `decimal`, `boolean`, `date` e `datetime`. Booleanos explícitos aceitam `true`, `false`, `1`, `0`. Datas usam `AAAA-MM-DD`; datetime usa ISO com `T`. Decimais usam ponto, sem separador de milhar. Valores incompatíveis são rejeitados, não aproximados por inferência. Limites de tamanho/expoente também se aplicam a números.

### Particularidades dos bancos

| Banco | Comportamento |
|---|---|
| SQLite | Identificadores entre aspas duplas; booleanos 1/0 e datas ISO como texto. A afinidade da tabela pode converter valores. |
| PostgreSQL | Identificadores entre aspas duplas; strings `E'...'`, booleanos nativos e literais DATE/TIMESTAMP; datetime com fuso preservado. |
| MySQL | Identificadores entre crases; textos em `CONVERT(X'...' USING utf8mb4)`, sem depender do modo de escape de barras; datetime com fuso exige conversão explícita para texto. |
| Oracle 19c+ | Nomes em maiúsculas e entre aspas duplas, booleanos 1/0, DATE/TIMESTAMP. `&` e quebras de linha usam `CHR`, evitando substituições SQL*Plus. Texto vazio é rejeitado porque Oracle o converte em NULL; datetime com fuso exige conversão para texto. |

A geração cobre INSERTs simples, não migrações de schema. Tamanho e precisão das colunas, encoding, constraints, privilégios e compatibilidade do cliente SQL continuam dependendo do banco de destino. Oracle não tem teste de integração com instância real nesta configuração. Strings longas podem exigir tratamento de LOB no destino. Revise o script antes de executá-lo. Não há COMMIT automático no script.

### Limites

| Recurso | Limite padrão |
|---|---|
| Arquivo | 5 MiB |
| Corpo HTTP | 5 MiB + 64 KiB para o formulário |
| Formulário multipart | 8 partes; 64 KiB por campo não arquivo |
| Dados exportados | 10.000 linhas, 100 colunas, 250.000 células |
| Célula textual | 32.767 caracteres |
| SQL gerado | 20 MiB |
| XLSX descompactado | 20 MiB e 1.000 entradas ZIP |
| Tempo | 10 s em verificações cooperativas; Gunicorn encerra worker travado após 30 s |

Um limite de linhas informado exporta somente o prefixo escolhido; o restante não é validado linha a linha. Sem limite explícito, exceder a cota falha em vez de truncar silenciosamente. CSV e XLSX são percorridos por linhas, mas o upload sempre respeita o limite em bytes. Parsers JSON/XLS e partes do XLSX podem alocar memória antes das verificações de linhas; mantenha os limites do contêiner/host.

## Endpoint

`POST /process` com `multipart/form-data`:

- `file-upload`: arquivo obrigatório.
- `table-name`: tabela ou schema.tabela.
- `dialect`: `sqlite` (padrão), `postgresql`, `mysql` ou `oracle`.
- `limit`: inteiro positivo opcional.
- `column-types`: objeto JSON opcional.
- `delimiter` e `null-marker`: opções CSV.
- `archive_type`: campo legado opcional (`auto`, `csv`, `json` ou `excel`); deve corresponder à extensão.

Resposta: download `application/sql`, `Cache-Control: no-store` e `X-Converted-Rows`. Falhas de validação retornam 400; limites do corpo/formulário, 413; excesso de requisições, 429. Erros internos retornam 500 sem detalhes dos dados. Não há sessão, cookie ou autenticação: é um conversor público sem histórico. Para uso interno restrito, proteja a implantação com o controle de acesso da organização.

## Testes e manutenção

```bash
pip install --require-hashes -r requirements-dev.txt
ruff check .
ruff format --check .
pytest -q
pip-audit --disable-pip --no-deps -r requirements.txt
```

Os testes cobrem round-trip SQLite, tipos/precisão, uploads inválidos, SQL injection como dado, limites, cabeçalhos, XML malicioso, concorrência e ausência de arquivos locais. Integrações PostgreSQL/MySQL só rodam com `TEST_POSTGRES_DSN`/`TEST_MYSQL_HOST` apontando para bancos descartáveis; a CI os provisiona e testa também o contêiner. Nunca use bancos de produção nessas variáveis.

`requirements.in` e `requirements-dev.in` declaram as dependências; os `.txt` contêm versões transitivas e hashes. Atualize de forma controlada em Python 3.12 e execute os testes:

```bash
pip-compile --upgrade --generate-hashes --strip-extras --no-emit-index-url --no-emit-trusted-host -o requirements.txt requirements.in
pip-compile --upgrade --allow-unsafe --generate-hashes --strip-extras --no-emit-index-url --no-emit-trusted-host -o requirements-dev.txt requirements-dev.in
```

Dependabot acompanha dependências, Actions e a imagem Docker. Actions usam SHAs fixos e permissões somente de leitura. Auditoria de pacotes não substitui revisão de código.

## Migração da versão anterior

- A gravação automática em `dados.db` foi removida. Bancos e `inserts.sql` antigos **não são apagados automaticamente**: revise sua retenção e remova-os do host conforme necessário.
- CSV passa a preservar texto e células vazias. Use o mapa de tipos e o marcador de NULL para conversões explícitas.
- Nomes de colunas são normalizados e citados; confirme que correspondem às colunas existentes. Oracle usa maiúsculas; tabelas Oracle criadas com nomes mistos entre aspas não são suportadas.
- Pandas foi substituído por leitores diretos (`csv`, `json`, `openpyxl`, `xlrd`) para controlar limites e preservar os valores. Não há dependência NumPy/Pandas.
- Atualize o comando de inicialização para Gunicorn e confirme a configuração do proxy antes de publicar.

## Estrutura

- `src/__init__.py`: fábrica Flask, limites HTTP e cabeçalhos.
- `src/views.py`: validação HTTP e download.
- `src/converter.py`: leitura, normalização, tipos e geração SQL.
- `src/templates/` e `src/static/`: interface em português, sem JavaScript ou recursos externos.
- `tests/`: regressões e integrações opcionais.
- `.github/workflows/ci.yml`: testes, auditoria e validação Docker.

Licença MIT: [License](License).
