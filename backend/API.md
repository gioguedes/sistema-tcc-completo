# API HTTP do painel

FastAPI que entrega ao front-end (Painel Aquícola) o que a ingestão MQTT grava em `leituras` e o serviço de ML grava em `previsoes`, faz o cadastro de tanques e dispositivos (UC01) e envia o comando do aerador ao nó sensor. Segue o contrato `docs/CONTRATO_API.md` do repositório do front-end.

## Rodar

Na pasta `backend/`, com o `.venv` ativo:

```powershell
pip install -r requirements.txt
```

No `.env`, além das variáveis que já existem, defina o segredo dos tokens (RNF05):

```powershell
python -c "import secrets; print(secrets.token_urlsafe(48))"
# copie a saída para API_JWT_SEGREDO= no .env
```

Crie um usuário (a senha é pedida no terminal). O usuário do seed não tem senha; o mesmo comando define uma para ele:

```powershell
python -m src.api.usuarios --email admin@exemplo.com --nome "Nome Sobrenome" --perfil admin
python -m src.api.usuarios --email operador@piscicultura.local
```

Suba a API (padrão: `http://127.0.0.1:8000`; documentação interativa em `/api/v1/docs`):

```powershell
python -m src.api
```

O front-end usa a API pelo proxy do Vite, na mesma origem. Na pasta do front: `VITE_USAR_MOCKS=false` e `API_PROXY_ALVO=http://127.0.0.1:8000` no `.env.development.local`, depois `npm run dev`.

Para haver leituras e previsões, rodam ao lado dela a ingestão (`python -m src.main`) e o serviço de ML. A API usa o mesmo broker MQTT do `.env` (`MQTT_BROKER_HOST`, `MQTT_BROKER_PORT`, `MQTT_TOPIC_PREFIX`) para publicar os comandos do aerador.

## Rotas

Todas com prefixo `/api/v1`. Fora `/auth/login`, `/auth/refresh` e `/auth/logout`, exigem `Authorization: Bearer <token>`.

| Rota | O que devolve |
|---|---|
| `POST /auth/login` | access token (15 min) no corpo e refresh token em cookie `HttpOnly; Secure; SameSite=Strict; Path=/api/v1/auth` (sessão, ou 30 dias com `lembrar`) |
| `POST /auth/refresh` | novo access token, a partir do cookie |
| `POST /auth/logout` | apaga o cookie |
| `GET` / `PATCH /auth/eu` | usuário logado; o PATCH altera nome e telefone (`+55…`) |
| `GET /especies` | catálogo de espécies |
| `GET /tanques`, `GET /tanques/{id}` | tanque com espécie, últimas leituras, OD estimado, nível atual e dispositivos |
| `GET /tanques/{id}/dispositivos` | dispositivos com sensores e o último comando do aerador (`ultimo_acionamento`) |
| `GET /tanques/{id}/leituras` | séries por grandeza: `bucket=raw\|5m\|1h`, `desde`, `ate`, `grandezas` |
| `GET /tanques/{id}/previsoes/atual` | último ciclo do ML: OD de agora (h = 0) e risco de 1 a 3 h |
| `GET /alertas` | lista vazia até o sub-projeto 4 (N8N) existir |
| `GET /eventos` | acionamentos do aerador, mais recentes primeiro (os alertas entram quando existirem) |
| `POST /tanques` | **admin** · cria o tanque e, se vier `dispositivo`, o nó com os 3 sensores, na mesma transação |
| `PATCH /tanques/{id}` | **admin** · altera os dados do tanque; "excluir" é mudar `status` para `inativo` |
| `POST /dispositivos` | **admin** · cria um nó em um tanque existente, com os 3 sensores |
| `PATCH /dispositivos/{id}` | **admin** · altera nome, MAC, modelo, firmware e IP |
| `PATCH /sensores/{id}` | **admin** · muda o status do sensor (`ativo`, `inativo`, `em_calibracao`) |
| `POST /dispositivos/{id}/aerador` | qualquer usuário · `{"acao": "ligar" \| "desligar"}` → **202** com o acionamento registrado |

## Regras que a API aplica

### Cadastro (UC01)

- **Permissão:** só o perfil `admin` (o `operador` recebe 403).
- **MAC:** aceito com `:`, `-` ou sem separador, e gravado como `aa:bb:cc:dd:ee:ff`, o formato que a ingestão procura. MAC repetido dá **409** no campo (`dispositivo.mac_address` ou `mac_address`), também quando dois cadastros chegam juntos.
- **Sensores:** todo dispositivo novo ganha os 3 sensores do nó (`TIPOS_SENSOR_PADRAO` do seed: SEN0161-V2, DS18B20, SEN0189). Sem eles a ingestão descarta as leituras. Se o catálogo `tipos_sensor` estiver vazio, a API cria os tipos como o seed faz.
- **Validação (422, mensagens em português no campo):**
  - nome obrigatório;
  - espécie do catálogo;
  - volume > 0;
  - quantidade ≥ 0;
  - data de povoamento que não esteja no futuro;
  - IP válido;
  - limites de tamanho das colunas.
- **Sem exclusão:** o tanque vai para `inativo` e o histórico fica.
- **Status do sensor:** o serviço de ML só lê sensores `ativo`. Com o pH ou a temperatura `inativo` ou `em_calibracao`, o tanque fica sem previsão.

### Comando do aerador (F-02)

- **Quem:** qualquer usuário autenticado (decisão do usuário em 09/10: quem cuida do tanque age na emergência).
- **O que a API faz:**
  1. grava o acionamento em `acionamentos_atuador` (`id_previsao` nulo, `motivo` = "Comando manual de <nome> pelo painel.");
  2. publica no broker;
  3. responde **202**. Se o broker não confirmar em 5 s, desfaz o registro e responde **503**.
- **Protocolo com o firmware:**
  - tópico `<MQTT_TOPIC_PREFIX>/<mac sem separador>/aerador`;
  - payload `{"acao": "ligar" | "desligar", "id": <acionamento>, "ts": <epoch UTC>}`;
  - QoS 1 e **retido**: o nó que reinicia ou volta de uma queda recebe o último comando ao assinar.
- **Firmware:** o nó precisa da versão que assina esse tópico (patch `firmware-aerador.patch` para o repositório `sistema`). Sem ela, o comando chega ao broker e nada acontece no relé.
- **Sem confirmação:** o nó ainda não informa o estado real do relé; o painel mostra o último comando enviado.
- **Automático × manual:** um acionamento é automático quando tem `id_previsao` (disparado por uma previsão, como o TC1 prevê para OD < 3 mg/L). Ninguém grava acionamento automático ainda.
- **Segurança:** no broker público (`broker.hivemq.com`) qualquer um que souber o tópico aciona o relé. Para uso real, broker privado com usuário e senha.

### Leitura

- **OD:** vem da linha `h = 0` de `previsoes` (`estimado: true`). `baixa_confianca` é `confianca < ML_CONFIANCA_MIN` (0,5), como no serviço de ML.
- **Previsão válida:** o último ciclo do ML tem no máximo 15 min (3 ciclos) e o tanque está `ativo`, com espécie. Fora disso, `previsoes/atual` volta sem nível, sem OD e sem horizontes. O `gerada_em` continua preenchido quando a previsão só está velha, para o painel mostrar "desatualizada desde…".
- **Nível atual do tanque:** o pior entre pH e temperatura da última leitura (regra de `ml/src/faixas.py`, copiada em `src/api/faixas.py`) e o nível do OD que o ML gravou. Não há outra classificação na API. *A confirmar com a equipe.*
- **Dispositivo online:** última leitura há no máximo 5 min (a ingestão não atualiza `status_conexao` nem `ultimo_heartbeat`).
- **Séries:** `date_bin` do PostgreSQL (dispensa TimescaleDB nos testes); a série de OD sai das linhas `h = 0`, uma a cada 5 min. Cada pedido aceita até 5.000 pontos.
- **Senhas:** `scrypt` da biblioteca padrão. Os tokens não guardam estado no servidor: sair apaga o cookie, e o access token expira em 15 min.

## Testes

```powershell
pytest tests/api
```

`test_cadastro.py` também confere que um dispositivo cadastrado pela API passa a ter as leituras aceitas pelo `LeituraProcessor` da ingestão.

`test_comando_aerador_mqtt.py` usa o broker de teste do `docker-compose` (`mosquitto-test`, porta 1884), como o teste de fumaça da equipe. Os outros testes da API usam um publicador falso e não precisam de broker.

Usam o mesmo banco de teste (`piscicultura_test`) e as mesmas fixtures dos testes da ingestão.

## Pendências

- Confirmação do estado do relé pelo nó (hoje o painel só sabe o último comando).
- Acionamento automático do aerador pelo OD estimado (TC1: abaixo de 3 mg/L).
- Broker MQTT privado e com senha antes de uso real.
- Alertas e eventos, quando o sub-projeto 4 gravar em `alertas`.
- WebSocket (Socket.IO). Enquanto ele não existe, o painel consulta a cada 30 s.
- Índice `previsoes (id_tanque, ts_previsao DESC)`: a busca do último ciclo hoje percorre a tabela. Basta para a escala do TCC.
- Limite de tentativas de login.
