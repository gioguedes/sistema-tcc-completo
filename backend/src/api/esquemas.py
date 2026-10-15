"""Formato das respostas, conforme docs/CONTRATO_API.md do front-end (Decimal sai como string)."""

from datetime import date, datetime, timezone
from decimal import Decimal
from typing import Annotated, Literal

from pydantic import AfterValidator, BaseModel, ConfigDict

# sempre em UTC ("...Z"), qualquer que seja o fuso da sessao do banco
DataHora = Annotated[datetime, AfterValidator(lambda d: d.astimezone(timezone.utc))]
NivelRisco = Literal["otimo", "atencao", "critico"]
Grandeza = Literal["ph", "temperatura", "turbidez", "od"]
StatusConexao = Literal["online", "offline"]


class _DoBanco(BaseModel):
    model_config = ConfigDict(from_attributes=True)


class UsuarioSaida(_DoBanco):
    id: int
    nome: str
    email: str
    telefone: str | None
    perfil: Literal["admin", "operador"]


class Token(BaseModel):
    access_token: str
    expira_em: DataHora


class EspecieSaida(_DoBanco):
    id: int
    nome_comum: str
    nome_cientifico: str
    ph_min: Decimal
    ph_max: Decimal
    temp_min: Decimal
    temp_max: Decimal
    od_min: Decimal
    od_max: Decimal


class LeituraAtual(BaseModel):
    grandeza: Grandeza
    valor: Decimal
    unidade: str
    ts: DataHora
    estimado: bool = False
    baixa_confianca: bool = False


class ResumoDispositivo(BaseModel):
    id: int
    nome: str
    status_conexao: StatusConexao
    ultima_leitura_em: DataHora | None


class TanqueSaida(BaseModel):
    id: int
    nome: str
    volume_litros: Decimal
    quantidade_peixes: int
    data_povoamento: date | None
    status: Literal["ativo", "manutencao", "inativo"]
    criado_em: DataHora
    especie: EspecieSaida | None
    nivel_risco: NivelRisco | None
    ultima_leitura_em: DataHora | None
    ultimas_leituras: list[LeituraAtual]
    dispositivos: list[ResumoDispositivo]


class SensorSaida(BaseModel):
    id: int
    grandeza: Grandeza
    modelo: str
    unidade: str
    status: Literal["ativo", "inativo", "em_calibracao"]
    data_instalacao: date


class AcionamentoSaida(_DoBanco):
    id: int
    acao: Literal["ligar", "desligar"]
    motivo: str | None
    ts_acionamento: DataHora


class UltimoAcionamento(AcionamentoSaida):
    # automatico = disparado por uma previsao (id_previsao preenchido); manual = comando do painel
    automatico: bool


class DispositivoSaida(BaseModel):
    id: int
    id_tanque: int
    nome: str
    modelo_esp32: str
    mac_address: str
    versao_firmware: str | None
    ip_local: str | None
    status_conexao: StatusConexao
    ultima_leitura_em: DataHora | None
    data_cadastro: DataHora
    sensores: list[SensorSaida]
    # ultimo comando do aerador; o no ainda nao confirma o estado do rele
    ultimo_acionamento: UltimoAcionamento | None


class Ponto(BaseModel):
    ts: DataHora
    valor: Decimal
    # so quando agregado; a rota omite os campos nulos
    min: Decimal | None = None
    max: Decimal | None = None


class Serie(BaseModel):
    grandeza: Grandeza
    unidade: str
    estimado: bool
    pontos: list[Ponto]


class Leituras(BaseModel):
    id_tanque: int
    bucket: Literal["raw", "5m", "1h"]
    desde: DataHora
    ate: DataHora
    series: list[Serie]


class PrevisaoSaida(_DoBanco):
    id: int
    parametro_critico: Grandeza
    valor_previsto: Decimal
    nivel_risco: NivelRisco
    horizonte_h: int
    confianca: Decimal | None
    # o ML so define baixa confianca para o OD estimado (h = 0); nos horizontes a confianca
    # e a probabilidade da classe prevista
    baixa_confianca: bool = False
    ts_previsao: DataHora


class EstimativaOd(BaseModel):
    valor: Decimal
    nivel_risco: NivelRisco
    confianca: Decimal | None
    baixa_confianca: bool


class PrevisaoAtual(BaseModel):
    id_tanque: int
    nivel_risco: NivelRisco | None
    gerada_em: DataHora | None
    od_atual: EstimativaOd | None
    horizontes: list[PrevisaoSaida]


class Pagina(BaseModel):
    itens: list[dict]
    total: int
    pagina: int
    por_pagina: int


class EventoAcionamento(BaseModel):
    tipo: Literal["acionamento"] = "acionamento"
    id: str
    id_tanque: int
    tanque_nome: str
    ocorrido_em: DataHora
    acao: Literal["ligar", "desligar"]
    automatico: bool
    motivo: str | None


class PaginaEventos(BaseModel):
    itens: list[EventoAcionamento]
    total: int
    pagina: int
    por_pagina: int
