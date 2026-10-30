from datetime import datetime, timezone
from typing import Annotated

from pydantic import BaseModel, Field

# Mesma faixa do CHECK ck_leit_valor da tabela leituras.
ValorLeitura = Annotated[float, Field(ge=-50, le=3000, allow_inf_nan=False)]


class LeituraMqttPayload(BaseModel):
    mac: str
    ts: int = Field(ge=0, le=4102444800)
    ph: ValorLeitura | None = None
    temperatura: ValorLeitura | None = None
    turbidez: ValorLeitura | None = None

    @property
    def ts_utc(self) -> datetime:
        return datetime.fromtimestamp(self.ts, tz=timezone.utc)

    @property
    def mac_com_separador(self) -> str:
        mac_normalizado = self.mac.replace(":", "").lower()
        pares = [mac_normalizado[i : i + 2] for i in range(0, len(mac_normalizado), 2)]
        return ":".join(pares)

    def valores_por_grandeza(self) -> dict[str, float]:
        candidatos = {"ph": self.ph, "temperatura": self.temperatura, "turbidez": self.turbidez}
        return {grandeza: valor for grandeza, valor in candidatos.items() if valor is not None}