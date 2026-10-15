from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class ConfigApi(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # segredo que assina os tokens (RNF05: credenciais em variaveis de ambiente).
    # Gerar com: python -c "import secrets; print(secrets.token_urlsafe(48))"
    api_jwt_segredo: str = Field(min_length=32)
    api_host: str = "127.0.0.1"
    api_porta: int = 8000
    api_acesso_minutos: int = 15
    # sem "lembrar de mim" o cookie morre com o navegador, e o token vale no maximo isso
    api_renovacao_horas: int = 12
    api_renovacao_dias_lembrar: int = 30
    # o navegador aceita cookie Secure em http://localhost; so desligar em teste por IP da rede
    api_cookie_seguro: bool = True

    # mesmo limiar do servico de ML (ML_CONFIANCA_MIN no .env do ml/)
    ml_confianca_min: float = 0.5
