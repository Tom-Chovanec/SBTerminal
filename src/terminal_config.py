import os
import yaml


# <MerchantTransactionID > 12345 < /MerchantTransactionID >
# <ZRNumber > 2010 < /ZRNumber >
# <DeviceNumber > 601 < /DeviceNumber >
# <DeviceType > 6 < /DeviceType >
# <TerminalID > Term01 < /TerminalID >


def save_config(config: dict):
    dir = "data"
    filepath = f"{dir}/config.yaml"

    if not os.path.exists(dir):
        os.makedirs(dir)

    with open(filepath, "w") as file:
        yaml.dump(config, file)
        print(f"INFO: Saved config to {filepath}")


default_config: dict = {
    'ip-address': '127.0.0.1',
    'port': 2605
}


def load_config() -> dict:
    dir = "data"
    filepath = f"{dir}/config.yaml"

    if not os.path.exists(dir):
        os.makedirs(dir)

    if not os.path.exists(filepath):
        with open(filepath, "w") as file:
            pass

    with open(filepath, 'r') as file:
        yaml_config: dict = yaml.safe_load(file)

    if not yaml_config:
        print(f'WARN: Config file "{filepath}" is empty, \
              creating new one using default config')
        save_config(default_config)
        return default_config

    print(f'INFO: Loaded config file "{filepath}"')
    return yaml_config
