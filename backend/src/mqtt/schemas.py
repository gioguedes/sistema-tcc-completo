from datetime import datetime, timezone

from pydantic import BaseModel


class LeituraMqttPayload(BaseModel):
    mac: str
    ts: int
    ph: float | None = None
    temperatura: float | None = None
    turbidez: float | None = None

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