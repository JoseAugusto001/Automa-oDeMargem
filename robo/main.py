import argparse
import os

import config
from robo_consulta_margem import executar_robo


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Robô Consulta Margem Banco Prata")
    parser.add_argument("--headless", action="store_true", help="Executar browser em modo headless")
    default_entrada = os.path.join(config.DIR_ENTRADA_PADRAO, config.ARQUIVO_ENTRADA_PADRAO)
    parser.add_argument("--entrada", default=default_entrada, help="Caminho do CSV de entrada")
    parser.add_argument("--saida", default=config.DIR_SAIDA_PADRAO, help="Pasta de saída do CSV")
    args = parser.parse_args()
    headless = args.headless or os.environ.get("ROBO_HEADLESS", "").strip().lower() in ("1", "true", "yes")
    executar_robo(caminho_entrada=args.entrada, dir_saida=args.saida, headless=headless)
