"""Cadastro de tanques, dispositivos e sensores (UC01), so para administradores.

Regras do UC01 e das decisoes registradas na auditoria do front (docs/AUDITORIA_FRONTEND.md):
- o tanque e o dispositivo opcional sao gravados na mesma transacao;
- o dispositivo nasce com os 3 sensores do no (pH, temperatura, turbidez); sem eles a
  ingestao descarta as leituras (I-07);
- MAC no formato que a ingestao grava e procura (aa:bb:cc:dd:ee:ff); repetido da 409;
- nao ha exclusao: o tanque passa a "inativo" e o historico fica (I-08).
"""

import ipaddress
import re
from contextlib import contextmanager
from datetime import date, datetime, timezone
from decimal import Decimal
from typing import Literal

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, field_validator
from pydantic_core import PydanticCustomError
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError

from src.api.dependencias import Administrador, Config, Sessao
from src.api.esquemas import DispositivoSaida, SensorSaida, TanqueSaida
from src.api.rotas.tanques import montar_dispositivos, montar_tanques, sensor_saida, tanque_ou_404
from src.db.models import Dispositivo, Especie, Sensor, Tanque, TipoSensor
from src.db.seed import TIPOS_SENSOR_PADRAO

router = APIRouter(tags=["cadastro"])

# aceita aa:bb:cc:dd:ee:ff, com hifen ou sem separador, como o formulario do front
REGEX_MAC = re.compile(r"^([0-9a-f]{2}[:-]?){5}[0-9a-f]{2}$", re.IGNORECASE)
VOLUME_MAXIMO = Decimal("999999.99")  # NUMERIC(8,2)
QUANTIDADE_MAXIMA = 2_147_483_647  # INTEGER
MODELO_PADRAO = "ESP32 DevKitC V4"  # default da coluna no DDL
MAC_REPETIDO = "Este endereço MAC já está cadastrado em outro dispositivo."


def _texto(valor: str | None, maximo: int, obrigatorio: str | None = None) -> str | None:
    valor = (valor or "").strip()
    if not valor:
        if obrigatorio:
            raise PydanticCustomError("obrigatorio", obrigatorio)
        return None
    if len(valor) > maximo:
        raise PydanticCustomError("texto_longo", f"Use no máximo {maximo} caracteres.")
    return valor


def normalizar_mac(valor: str) -> str:
    # mesmo formato de LeituraMqttPayload.mac_com_separador, que a ingestao usa para achar o no
    hexa = re.sub(r"[:-]", "", valor).lower()
    return ":".join(hexa[i : i + 2] for i in range(0, 12, 2))


class DadosTanque(BaseModel):
    nome: str
    id_especie: int
    volume_litros: Decimal
    quantidade_peixes: int
    data_povoamento: date | None = None
    status: Literal["ativo", "manutencao", "inativo"] = "ativo"

    @field_validator("nome")
    @classmethod
    def _nome(cls, valor: str) -> str:
        return _texto(valor, 120, "Informe o nome do tanque.")

    @field_validator("volume_litros")
    @classmethod
    def _volume(cls, valor: Decimal) -> Decimal:
        if valor <= 0:
            raise PydanticCustomError("volume_invalido", "O volume deve ser maior que zero.")
        if valor > VOLUME_MAXIMO:
            raise PydanticCustomError("volume_invalido", "Volume acima do limite permitido.")
        return valor

    @field_validator("quantidade_peixes")
    @classmethod
    def _quantidade(cls, valor: int) -> int:
        if valor < 0:
            raise PydanticCustomError("quantidade_invalida", "A quantidade não pode ser negativa.")
        if valor > QUANTIDADE_MAXIMA:
            raise PydanticCustomError("quantidade_invalida", "Quantidade acima do limite permitido.")
        return valor

    @field_validator("data_povoamento")
    @classmethod
    def _data(cls, valor: date | None) -> date | None:
        # comparado com a data em UTC, que nunca fica atras da data no Brasil
        if valor is not None and valor > datetime.now(timezone.utc).date():
            raise PydanticCustomError("data_futura", "A data não pode estar no futuro.")
        return valor


class DadosDispositivo(BaseModel):
    nome: str
    mac_address: str
    modelo_esp32: str | None = None
    versao_firmware: str | None = None
    ip_local: str | None = None

    @field_validator("nome")
    @classmethod
    def _nome(cls, valor: str) -> str:
        return _texto(valor, 120, "Informe o nome do dispositivo.")

    @field_validator("mac_address")
    @classmethod
    def _mac(cls, valor: str) -> str:
        valor = _texto(valor, 17, "Informe o endereço MAC do ESP32.")
        if not REGEX_MAC.match(valor):
            raise PydanticCustomError("mac_invalido", "Use o formato AA:BB:CC:DD:EE:FF.")
        return normalizar_mac(valor)

    @field_validator("modelo_esp32")
    @classmethod
    def _modelo(cls, valor: str | None) -> str | None:
        return _texto(valor, 60)

    @field_validator("versao_firmware")
    @classmethod
    def _firmware(cls, valor: str | None) -> str | None:
        return _texto(valor, 30)

    @field_validator("ip_local")
    @classmethod
    def _ip(cls, valor: str | None) -> str | None:
        valor = _texto(valor, 45)
        if valor is None:
            return None
        try:
            return str(ipaddress.ip_address(valor))
        except ValueError:
            raise PydanticCustomError("ip_invalido", "Informe um IP válido, como 192.168.0.20.") from None


class NovoTanque(DadosTanque):
    dispositivo: DadosDispositivo | None = None


class NovoDispositivo(DadosDispositivo):
    id_tanque: int


class DadosSensor(BaseModel):
    status: Literal["ativo", "inativo", "em_calibracao"]


def _erro_de_campo(status: int, caminho: list[str], mensagem: str) -> HTTPException:
    # mesmo formato dos erros de validacao do FastAPI, para o front marcar o campo
    tipo = "conflict" if status == 409 else "value_error"
    return HTTPException(status, [{"loc": ["body", *caminho], "msg": mensagem, "type": tipo}])


def _checar_especie(sessao, id_especie: int) -> None:
    if sessao.get(Especie, id_especie) is None:
        raise _erro_de_campo(422, ["id_especie"], "Selecione uma espécie do catálogo.")


def _checar_mac(sessao, mac: str, caminho: list[str], ignorar_id: int | None = None) -> None:
    existente = sessao.scalar(select(Dispositivo.id).where(func.lower(Dispositivo.mac_address) == mac))
    if existente is not None and existente != ignorar_id:
        raise _erro_de_campo(409, caminho, MAC_REPETIDO)


@contextmanager
def _transacao(sessao, caminho_mac: list[str]):
    try:
        yield
        sessao.commit()
    except IntegrityError as erro:
        sessao.rollback()
        # outra requisicao gravou o mesmo MAC entre a checagem e o INSERT. O nome da restricao
        # muda (uq_disp_mac no DDL, outro no banco de teste); o detalhe sempre cita a coluna
        detalhe = getattr(getattr(erro.orig, "diag", None), "message_detail", None) or ""
        if "(mac_address)" in detalhe:
            raise _erro_de_campo(409, caminho_mac, MAC_REPETIDO) from None
        raise


def _tipos_do_no(sessao) -> list[TipoSensor]:
    # os sensores fisicos do no sao os do catalogo do seed; o que faltar e criado como o seed faz
    tipos = []
    for dados in TIPOS_SENSOR_PADRAO:
        tipo = sessao.scalar(select(TipoSensor).where(TipoSensor.modelo == dados["modelo"]))
        if tipo is None:
            tipo = TipoSensor(**dados)
            sessao.add(tipo)
        tipos.append(tipo)
    sessao.flush()
    return tipos


def _criar_dispositivo(sessao, dados: DadosDispositivo, id_tanque: int) -> Dispositivo:
    dispositivo = Dispositivo(
        id_tanque=id_tanque,
        nome=dados.nome,
        modelo_esp32=dados.modelo_esp32 or MODELO_PADRAO,
        mac_address=dados.mac_address,
        versao_firmware=dados.versao_firmware,
        ip_local=dados.ip_local,
        status_conexao="offline",
        ultimo_heartbeat=None,
        data_cadastro=datetime.now(timezone.utc),
    )
    sessao.add(dispositivo)
    sessao.flush()
    for tipo in _tipos_do_no(sessao):
        sessao.add(
            Sensor(
                id_dispositivo=dispositivo.id,
                id_tipo=tipo.id,
                id_tanque=id_tanque,
                data_instalacao=date.today(),
                status="ativo",
            )
        )
    return dispositivo


@router.post("/tanques", status_code=201, response_model=TanqueSaida)
def criar_tanque(dados: NovoTanque, admin: Administrador, sessao: Sessao, config: Config) -> TanqueSaida:
    _checar_especie(sessao, dados.id_especie)
    if dados.dispositivo is not None:
        _checar_mac(sessao, dados.dispositivo.mac_address, ["dispositivo", "mac_address"])

    tanque = Tanque(
        id_usuario=admin.id, criado_em=datetime.now(timezone.utc), **dados.model_dump(exclude={"dispositivo"})
    )
    with _transacao(sessao, ["dispositivo", "mac_address"]):
        sessao.add(tanque)
        sessao.flush()
        if dados.dispositivo is not None:
            _criar_dispositivo(sessao, dados.dispositivo, tanque.id)
    return montar_tanques(sessao, [tanque], config)[0]


@router.patch("/tanques/{id_tanque}", response_model=TanqueSaida)
def atualizar_tanque(
    id_tanque: int, dados: DadosTanque, _: Administrador, sessao: Sessao, config: Config
) -> TanqueSaida:
    tanque = tanque_ou_404(sessao, id_tanque)
    _checar_especie(sessao, dados.id_especie)
    for campo, valor in dados.model_dump().items():
        setattr(tanque, campo, valor)
    sessao.commit()
    return montar_tanques(sessao, [tanque], config)[0]


@router.post("/dispositivos", status_code=201, response_model=DispositivoSaida)
def criar_dispositivo(dados: NovoDispositivo, _: Administrador, sessao: Sessao) -> DispositivoSaida:
    if sessao.get(Tanque, dados.id_tanque) is None:
        raise _erro_de_campo(422, ["id_tanque"], "Tanque não encontrado.")
    _checar_mac(sessao, dados.mac_address, ["mac_address"])
    with _transacao(sessao, ["mac_address"]):
        dispositivo = _criar_dispositivo(sessao, dados, dados.id_tanque)
    return montar_dispositivos(sessao, [dispositivo])[0]


@router.patch("/dispositivos/{id_dispositivo}", response_model=DispositivoSaida)
def atualizar_dispositivo(
    id_dispositivo: int, dados: DadosDispositivo, _: Administrador, sessao: Sessao
) -> DispositivoSaida:
    dispositivo = sessao.get(Dispositivo, id_dispositivo)
    if dispositivo is None:
        raise HTTPException(404, "Dispositivo não encontrado.")
    _checar_mac(sessao, dados.mac_address, ["mac_address"], ignorar_id=dispositivo.id)
    with _transacao(sessao, ["mac_address"]):
        dispositivo.nome = dados.nome
        dispositivo.mac_address = dados.mac_address
        dispositivo.modelo_esp32 = dados.modelo_esp32 or dispositivo.modelo_esp32
        dispositivo.versao_firmware = dados.versao_firmware
        dispositivo.ip_local = dados.ip_local
    return montar_dispositivos(sessao, [dispositivo])[0]


@router.patch("/sensores/{id_sensor}", response_model=SensorSaida)
def atualizar_sensor(id_sensor: int, dados: DadosSensor, _: Administrador, sessao: Sessao) -> SensorSaida:
    sensor = sessao.get(Sensor, id_sensor)
    if sensor is None:
        raise HTTPException(404, "Sensor não encontrado.")
    # o servico de ML so le sensores "ativo": pH ou temperatura fora disso deixa o tanque sem previsao
    sensor.status = dados.status
    sessao.commit()
    return sensor_saida(sensor, sessao.get(TipoSensor, sensor.id_tipo))
