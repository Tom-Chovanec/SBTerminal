import os
import yaml


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
    'port': 2605,
    'send-rsp-before-timeout': 'true',
    'card-issuer': 'VS',
    'card-type': 'CHIP',
    'card-number': '**********1234',
    'expiration-date': '2512',
    'hashed-card-number': '437B12A684A75C61235260',
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

    original_keys = set(yaml_config.keys())
    for key, value in default_config.items():
        yaml_config.setdefault(key, value)
    new_keys = set(yaml_config.keys()) - original_keys
    if new_keys:
        print(f'WARN: Keys "{new_keys}" are missing from "{filepath}", loading them from default config')

    return yaml_config
