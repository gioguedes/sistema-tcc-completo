-- =====================================================================
-- APENDICE A - Script DDL do Banco de Dados
-- Sistema de Monitoramento de Qualidade da Agua em Piscicultura
-- SGBD: PostgreSQL 16 + extensao TimescaleDB (series temporais)
-- Modelagem: relacional, normalizada ate a 3FN | 11 entidades
-- Autores (2026)
-- =====================================================================

CREATE EXTENSION IF NOT EXISTS timescaledb;

-- ---------------------------------------------------------------------
-- 1. USUARIOS
-- ---------------------------------------------------------------------
CREATE TABLE usuarios (
    id            BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    nome          VARCHAR(120)  NOT NULL,
    email         VARCHAR(160)  NOT NULL,
    senha_hash    VARCHAR(255)  NOT NULL,
    telefone      VARCHAR(20),
    perfil        VARCHAR(20)   NOT NULL DEFAULT 'operador',
    criado_em     TIMESTAMPTZ   NOT NULL DEFAULT now(),
    CONSTRAINT uq_usuarios_email   UNIQUE (email),
    CONSTRAINT ck_usuarios_perfil  CHECK (perfil IN ('admin','operador'))
);

-- ---------------------------------------------------------------------
-- 2. ESPECIES (catalogo: faixas ideais por especie)
-- ---------------------------------------------------------------------
CREATE TABLE especies (
    id               BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    nome_comum       VARCHAR(120) NOT NULL,
    nome_cientifico  VARCHAR(160) NOT NULL,
    ph_min           NUMERIC(4,2) NOT NULL,
    ph_max           NUMERIC(4,2) NOT NULL,
    temp_min         NUMERIC(4,1) NOT NULL,
    temp_max         NUMERIC(4,1) NOT NULL,
    od_min           NUMERIC(4,2) NOT NULL,
    od_max           NUMERIC(4,2) NOT NULL,
    CONSTRAINT uq_especies_cientifico UNIQUE (nome_cientifico),
    CONSTRAINT ck_especies_ph    CHECK (ph_min   >= 0  AND ph_max   <= 14 AND ph_min   < ph_max),
    CONSTRAINT ck_especies_temp  CHECK (temp_min >= -10 AND temp_max <= 50 AND temp_min < temp_max),
    CONSTRAINT ck_especies_od    CHECK (od_min   >= 0  AND od_max   <= 20 AND od_min   < od_max)
);

-- ---------------------------------------------------------------------
-- 3. TANQUES
-- ---------------------------------------------------------------------
CREATE TABLE tanques (
    id               BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    id_usuario       BIGINT       NOT NULL,
    id_especie       BIGINT,
    nome             VARCHAR(120) NOT NULL,
    volume_litros    NUMERIC(8,2) NOT NULL,
    quantidade_peixes INTEGER     NOT NULL DEFAULT 0,
    data_povoamento  DATE,
    status           VARCHAR(20)  NOT NULL DEFAULT 'ativo',
    criado_em        TIMESTAMPTZ  NOT NULL DEFAULT now(),
    CONSTRAINT fk_tanques_usuario FOREIGN KEY (id_usuario) REFERENCES usuarios(id) ON DELETE CASCADE,
    CONSTRAINT fk_tanques_especie FOREIGN KEY (id_especie) REFERENCES especies(id) ON DELETE SET NULL,
    CONSTRAINT ck_tanques_volume  CHECK (volume_litros > 0),
    CONSTRAINT ck_tanques_qtd     CHECK (quantidade_peixes >= 0),
    CONSTRAINT ck_tanques_status  CHECK (status IN ('ativo','manutencao','inativo'))
);

-- ---------------------------------------------------------------------
-- 4. DISPOSITIVOS (nos sensores ESP32)
-- ---------------------------------------------------------------------
CREATE TABLE dispositivos (
    id               BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    id_tanque        BIGINT       NOT NULL,
    nome             VARCHAR(120) NOT NULL,
    modelo_esp32     VARCHAR(60)  NOT NULL DEFAULT 'ESP32 DevKitC V4',
    mac_address      VARCHAR(17)  NOT NULL,
    versao_firmware  VARCHAR(30),
    ip_local         INET,
    status_conexao   VARCHAR(20)  NOT NULL DEFAULT 'offline',
    ultimo_heartbeat TIMESTAMPTZ,
    data_cadastro    TIMESTAMPTZ  NOT NULL DEFAULT now(),
    CONSTRAINT fk_disp_tanque   FOREIGN KEY (id_tanque) REFERENCES tanques(id) ON DELETE CASCADE,
    CONSTRAINT uq_disp_mac      UNIQUE (mac_address),
    CONSTRAINT ck_disp_conexao  CHECK (status_conexao IN ('online','offline'))
);

-- ---------------------------------------------------------------------
-- 5. TIPOS_SENSOR (catalogo de modelos e faixas de medicao)
-- ---------------------------------------------------------------------
CREATE TABLE tipos_sensor (
    id           BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    grandeza     VARCHAR(30)  NOT NULL,
    modelo       VARCHAR(80)  NOT NULL,
    unidade      VARCHAR(20)  NOT NULL,
    faixa_min    NUMERIC(8,2) NOT NULL,
    faixa_max    NUMERIC(8,2) NOT NULL,
    CONSTRAINT uq_tipos_modelo  UNIQUE (modelo),
    CONSTRAINT ck_tipos_grandeza CHECK (grandeza IN ('ph','temperatura','turbidez','od')),
    CONSTRAINT ck_tipos_faixa   CHECK (faixa_min < faixa_max)
);

-- ---------------------------------------------------------------------
-- 6. SENSORES (instancias fisicas instaladas)
-- ---------------------------------------------------------------------
CREATE TABLE sensores (
    id               BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    id_dispositivo   BIGINT       NOT NULL,
    id_tipo          BIGINT       NOT NULL,
    id_tanque        BIGINT       NOT NULL,
    data_instalacao  DATE         NOT NULL DEFAULT CURRENT_DATE,
    status           VARCHAR(20)  NOT NULL DEFAULT 'ativo',
    CONSTRAINT fk_sens_disp   FOREIGN KEY (id_dispositivo) REFERENCES dispositivos(id) ON DELETE CASCADE,
    CONSTRAINT fk_sens_tipo   FOREIGN KEY (id_tipo)        REFERENCES tipos_sensor(id),
    CONSTRAINT fk_sens_tanque FOREIGN KEY (id_tanque)      REFERENCES tanques(id) ON DELETE CASCADE,
    CONSTRAINT ck_sens_status CHECK (status IN ('ativo','inativo','em_calibracao'))
);

-- ---------------------------------------------------------------------
-- 7. LEITURAS (serie temporal de alta cadencia -> HYPERTABLE)
--    PK composta (id, ts) exigida pelo TimescaleDB: a coluna de
--    particionamento deve integrar a chave primaria.
-- ---------------------------------------------------------------------
CREATE TABLE leituras (
    id         BIGINT GENERATED ALWAYS AS IDENTITY,
    id_sensor  BIGINT        NOT NULL,
    valor      NUMERIC(10,4) NOT NULL,
    unidade    VARCHAR(20)   NOT NULL,
    ts         TIMESTAMPTZ   NOT NULL DEFAULT now(),
    CONSTRAINT pk_leituras   PRIMARY KEY (id, ts),
    CONSTRAINT fk_leit_sensor FOREIGN KEY (id_sensor) REFERENCES sensores(id) ON DELETE CASCADE,
    CONSTRAINT ck_leit_valor  CHECK (valor BETWEEN -50 AND 3000)
);

-- Conversao em hypertable particionada por tempo (chunks de 7 dias)
SELECT create_hypertable('leituras', 'ts',
                         chunk_time_interval => INTERVAL '7 days');

-- Indice composto para consultas de janela recente por sensor
CREATE INDEX ix_leituras_sensor_ts ON leituras (id_sensor, ts DESC);

-- Compressao colunar segmentada por sensor
ALTER TABLE leituras SET (
    timescaledb.compress,
    timescaledb.compress_segmentby = 'id_sensor',
    timescaledb.compress_orderby   = 'ts DESC'
);

-- Politica: comprimir chunks com mais de 30 dias
SELECT add_compression_policy('leituras', INTERVAL '30 days');

-- ---------------------------------------------------------------------
-- 8. PREVISOES (saidas do modelo de ML por tanque)
-- ---------------------------------------------------------------------
CREATE TABLE previsoes (
    id                 BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    id_tanque          BIGINT       NOT NULL,
    parametro_critico  VARCHAR(30)  NOT NULL,
    valor_previsto     NUMERIC(10,4) NOT NULL,
    nivel_risco        VARCHAR(20)  NOT NULL,
    horizonte_h        SMALLINT     NOT NULL,
    confianca          NUMERIC(5,4),
    ts_previsao        TIMESTAMPTZ  NOT NULL DEFAULT now(),
    CONSTRAINT fk_prev_tanque  FOREIGN KEY (id_tanque) REFERENCES tanques(id) ON DELETE CASCADE,
    CONSTRAINT ck_prev_nivel   CHECK (nivel_risco IN ('otimo','atencao','critico')),
    CONSTRAINT ck_prev_horiz   CHECK (horizonte_h IN (1,2,3)),
    CONSTRAINT ck_prev_param   CHECK (parametro_critico IN ('ph','temperatura','turbidez','od')),
    CONSTRAINT ck_prev_conf    CHECK (confianca IS NULL OR confianca BETWEEN 0 AND 1)
);

-- ---------------------------------------------------------------------
-- 9. ALERTAS
-- ---------------------------------------------------------------------
CREATE TABLE alertas (
    id            BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    id_previsao   BIGINT,
    id_tanque     BIGINT       NOT NULL,
    id_usuario    BIGINT       NOT NULL,
    mensagem      TEXT         NOT NULL,
    canal         VARCHAR(20)  NOT NULL DEFAULT 'whatsapp',
    status        VARCHAR(20)  NOT NULL DEFAULT 'pendente',
    workflow_id   VARCHAR(80),
    ts_envio      TIMESTAMPTZ,
    criado_em     TIMESTAMPTZ  NOT NULL DEFAULT now(),
    CONSTRAINT fk_alert_prev    FOREIGN KEY (id_previsao) REFERENCES previsoes(id) ON DELETE SET NULL,
    CONSTRAINT fk_alert_tanque  FOREIGN KEY (id_tanque)   REFERENCES tanques(id) ON DELETE CASCADE,
    CONSTRAINT fk_alert_usuario FOREIGN KEY (id_usuario)  REFERENCES usuarios(id) ON DELETE CASCADE,
    CONSTRAINT ck_alert_canal   CHECK (canal IN ('whatsapp','email','sms')),
    CONSTRAINT ck_alert_status  CHECK (status IN ('pendente','enviado','falha'))
);

-- ---------------------------------------------------------------------
-- 10. EVENTOS_MORTALIDADE
-- ---------------------------------------------------------------------
CREATE TABLE eventos_mortalidade (
    id                BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    id_tanque         BIGINT       NOT NULL,
    id_usuario        BIGINT       NOT NULL,
    quantidade_peixes INTEGER      NOT NULL,
    causa_provavel    VARCHAR(160),
    parametros_momento JSONB,
    data_hora         TIMESTAMPTZ  NOT NULL DEFAULT now(),
    CONSTRAINT fk_mort_tanque  FOREIGN KEY (id_tanque)  REFERENCES tanques(id) ON DELETE CASCADE,
    CONSTRAINT fk_mort_usuario FOREIGN KEY (id_usuario) REFERENCES usuarios(id) ON DELETE CASCADE,
    CONSTRAINT ck_mort_qtd     CHECK (quantidade_peixes > 0)
);

-- ---------------------------------------------------------------------
-- 11. ACIONAMENTOS_ATUADOR (rele/aerador)
-- ---------------------------------------------------------------------
CREATE TABLE acionamentos_atuador (
    id             BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    id_dispositivo BIGINT       NOT NULL,
    id_tanque      BIGINT       NOT NULL,
    id_previsao    BIGINT,
    acao           VARCHAR(10)  NOT NULL,
    motivo         VARCHAR(160),
    ts_acionamento TIMESTAMPTZ  NOT NULL DEFAULT now(),
    CONSTRAINT fk_acio_disp   FOREIGN KEY (id_dispositivo) REFERENCES dispositivos(id) ON DELETE CASCADE,
    CONSTRAINT fk_acio_tanque FOREIGN KEY (id_tanque)      REFERENCES tanques(id) ON DELETE CASCADE,
    CONSTRAINT fk_acio_prev   FOREIGN KEY (id_previsao)    REFERENCES previsoes(id) ON DELETE SET NULL,
    CONSTRAINT ck_acio_acao   CHECK (acao IN ('ligar','desligar'))
);

-- ---------------------------------------------------------------------
-- CONTINUOUS AGGREGATE (recurso TSDB): medias horarias pre-calculadas
-- para acelerar graficos historicos do dashboard (RNF02).
-- ---------------------------------------------------------------------
CREATE MATERIALIZED VIEW leituras_media_horaria
WITH (timescaledb.continuous) AS
SELECT id_sensor,
       time_bucket(INTERVAL '1 hour', ts) AS hora,
       AVG(valor) AS valor_medio,
       MIN(valor) AS valor_min,
       MAX(valor) AS valor_max
FROM leituras
GROUP BY id_sensor, hora
WITH NO DATA;

-- Politica de atualizacao incremental do continuous aggregate
SELECT add_continuous_aggregate_policy('leituras_media_horaria',
    start_offset      => INTERVAL '3 days',
    end_offset        => INTERVAL '1 hour',
    schedule_interval => INTERVAL '1 hour');

-- =====================================================================
-- FIM DO SCRIPT DDL
-- =====================================================================
