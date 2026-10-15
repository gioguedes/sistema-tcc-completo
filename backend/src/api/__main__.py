import logging

import uvicorn

from src.api.app import criar_app
from src.api.config import ConfigApi


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    config = ConfigApi()
    uvicorn.run(criar_app(config), host=config.api_host, port=config.api_porta)


if __name__ == "__main__":
    main()
