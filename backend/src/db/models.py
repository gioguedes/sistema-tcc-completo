from datetime import date, datetime

from sqlalchemy import (
    BigInteger,
    CheckConstraint,
    Date,
    DateTime,
    ForeignKey,
    Identity,
    Index,
    Numeric,
    SmallInteger,
    String,
    UniqueConstraint,
    text,
)
from sqlalchemy.dialects.postgresql import INET
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


class Usuario(Base):
    __tablename__ = "usuarios"
    __table_args__ = (
        CheckConstraint("perfil IN ('admin','operador')", name="ck_usuarios_perfil"),
    )

    id: Mapped[int] = mapped_column(BigInteger, Identity(always=True), primary_key=True)
    nome: Mapped[str] = mapped_column(String(120))
    email: Mapped[str] = mapped_column(String(160), unique=True)
    senha_hash: Mapped[str] = mapped_column(String(255))
    telefone: Mapped[str | None] = mapped_column(String(20))
    perfil: Mapped[str] = mapped_column(String(20))
    criado_em: Mapped[datetime] = mapped_column(DateTime(timezone=True))


class Especie(Base):
    __tablename__ = "especies"
    __table_args__ = (
        CheckConstraint("ph_min >= 0 AND ph_max <= 14 AND ph_min < ph_max", name="ck_especies_ph"),
        CheckConstraint(
            "temp_min >= -10 AND temp_max <= 50 AND temp_min < temp_max", name="ck_especies_temp"
        ),
        CheckConstraint("od_min >= 0 AND od_max <= 20 AND od_min < od_max", name="ck_especies_od"),
    )

    id: Mapped[int] = mapped_column(BigInteger, Identity(always=True), primary_key=True)
    nome_comum: Mapped[str] = mapped_column(String(120))
    nome_cientifico: Mapped[str] = mapped_column(String(160), unique=True)
    ph_min: Mapped[float] = mapped_column(Numeric(4, 2))
    ph_max: Mapped[float] = mapped_column(Numeric(4, 2))
    temp_min: Mapped[float] = mapped_column(Numeric(4, 1))
    temp_max: Mapped[float] = mapped_column(Numeric(4, 1))
    od_min: Mapped[float] = mapped_column(Numeric(4, 2))
    od_max: Mapped[float] = mapped_column(Numeric(4, 2))


class Tanque(Base):
    __tablename__ = "tanques"
    __table_args__ = (
        CheckConstraint("volume_litros > 0", name="ck_tanques_volume"),
        CheckConstraint("quantidade_peixes >= 0", name="ck_tanques_qtd"),
        CheckConstraint("status IN ('ativo','manutencao','inativo')", name="ck_tanques_status"),
    )

    id: Mapped[int] = mapped_column(BigInteger, Identity(always=True), primary_key=True)
    id_usuario: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("usuarios.id", ondelete="CASCADE")
    )
    id_especie: Mapped[int | None] = mapped_column(
        BigInteger, ForeignKey("especies.id", ondelete="SET NULL")
    )
    nome: Mapped[str] = mapped_column(String(120))
    volume_litros: Mapped[float] = mapped_column(Numeric(8, 2))
    quantidade_peixes: Mapped[int]
    data_povoamento: Mapped[date | None] = mapped_column(Date)
    status: Mapped[str] = mapped_column(String(20))
    criado_em: Mapped[datetime] = mapped_column(DateTime(timezone=True))


class Dispositivo(Base):
    __tablename__ = "dispositivos"
    __table_args__ = (
        CheckConstraint("status_conexao IN ('online','offline')", name="ck_disp_conexao"),
    )

    id: Mapped[int] = mapped_column(BigInteger, Identity(always=True), primary_key=True)
    id_tanque: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("tanques.id", ondelete="CASCADE")
    )
    nome: Mapped[str] = mapped_column(String(120))
    modelo_esp32: Mapped[str] = mapped_column(String(60))
    mac_address: Mapped[str] = mapped_column(String(17), unique=True)
    versao_firmware: Mapped[str | None] = mapped_column(String(30))
    ip_local: Mapped[str | None] = mapped_column(INET)
    status_conexao: Mapped[str] = mapped_column(String(20))
    ultimo_heartbeat: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    data_cadastro: Mapped[datetime] = mapped_column(DateTime(timezone=True))


class TipoSensor(Base):
    __tablename__ = "tipos_sensor"
    __table_args__ = (
        CheckConstraint("grandeza IN ('ph','temperatura','turbidez','od')", name="ck_tipos_grandeza"),
        CheckConstraint("faixa_min < faixa_max", name="ck_tipos_faixa"),
    )

    id: Mapped[int] = mapped_column(BigInteger, Identity(always=True), primary_key=True)
    grandeza: Mapped[str] = mapped_column(String(30))
    modelo: Mapped[str] = mapped_column(String(80), unique=True)
    unidade: Mapped[str] = mapped_column(String(20))
    faixa_min: Mapped[float] = mapped_column(Numeric(8, 2))
    faixa_max: Mapped[float] = mapped_column(Numeric(8, 2))


class Sensor(Base):
    __tablename__ = "sensores"
    __table_args__ = (
        CheckConstraint("status IN ('ativo','inativo','em_calibracao')", name="ck_sens_status"),
    )

    id: Mapped[int] = mapped_column(BigInteger, Identity(always=True), primary_key=True)
    id_dispositivo: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("dispositivos.id", ondelete="CASCADE")
    )
    id_tipo: Mapped[int] = mapped_column(BigInteger, ForeignKey("tipos_sensor.id"))
    id_tanque: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("tanques.id", ondelete="CASCADE")
    )
    data_instalacao: Mapped[date] = mapped_column(Date)
    status: Mapped[str] = mapped_column(String(20))


class Leitura(Base):
    __tablename__ = "leituras"
    __table_args__ = (
        CheckConstraint("valor BETWEEN -50 AND 3000", name="ck_leit_valor"),
        Index("ix_leituras_sensor_ts", "id_sensor", text("ts DESC")),
        Index("leituras_ts_idx", text("ts DESC")),
        UniqueConstraint("id_sensor", "ts", name="uq_leituras_sensor_ts"),
    )

    id: Mapped[int] = mapped_column(BigInteger, Identity(always=True), primary_key=True)
    ts: Mapped[datetime] = mapped_column(DateTime(timezone=True), primary_key=True)
    id_sensor: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("sensores.id", ondelete="CASCADE")
    )
    valor: Mapped[float] = mapped_column(Numeric(10, 4))
    unidade: Mapped[str] = mapped_column(String(20))


class Previsao(Base):
    __tablename__ = "previsoes"
    __table_args__ = (
        CheckConstraint("nivel_risco IN ('otimo','atencao','critico')", name="ck_prev_nivel"),
        # h=0 e a estimativa de OD do instante atual (desvio declarado do DDL
        # do TC1, que so previa 1, 2 e 3; ver spec do sub-projeto 3)
        CheckConstraint("horizonte_h IN (0,1,2,3)", name="ck_prev_horiz"),
        CheckConstraint(
            "parametro_critico IN ('ph','temperatura','turbidez','od')", name="ck_prev_param"
        ),
        CheckConstraint("confianca IS NULL OR confianca BETWEEN 0 AND 1", name="ck_prev_conf"),
    )

    id: Mapped[int] = mapped_column(BigInteger, Identity(always=True), primary_key=True)
    id_tanque: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("tanques.id", ondelete="CASCADE", name="fk_prev_tanque")
    )
    parametro_critico: Mapped[str] = mapped_column(String(30))
    valor_previsto: Mapped[float] = mapped_column(Numeric(10, 4))
    nivel_risco: Mapped[str] = mapped_column(String(20))
    horizonte_h: Mapped[int] = mapped_column(SmallInteger)
    confianca: Mapped[float | None] = mapped_column(Numeric(5, 4))
    ts_previsao: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=text("now()")
    )


class AcionamentoAtuador(Base):
    __tablename__ = "acionamentos_atuador"
    __table_args__ = (CheckConstraint("acao IN ('ligar','desligar')", name="ck_acio_acao"),)

    id: Mapped[int] = mapped_column(BigInteger, Identity(always=True), primary_key=True)
    id_dispositivo: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("dispositivos.id", ondelete="CASCADE", name="fk_acio_disp")
    )
    id_tanque: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("tanques.id", ondelete="CASCADE", name="fk_acio_tanque")
    )
    # preenchido quando o acionamento vem de uma previsao (automatico); nulo no comando manual
    id_previsao: Mapped[int | None] = mapped_column(
        BigInteger, ForeignKey("previsoes.id", ondelete="SET NULL", name="fk_acio_prev")
    )
    acao: Mapped[str] = mapped_column(String(10))
    motivo: Mapped[str | None] = mapped_column(String(160))
    ts_acionamento: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=text("now()")
    )
