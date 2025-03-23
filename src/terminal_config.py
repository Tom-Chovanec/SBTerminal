import os
import yaml
from dataclasses import dataclass

@dataclass
class Config:
    ip_address: str
    port: int
    send_rsp_before_timeout: bool
    card_issuer: str
    card_type: str
    card_number: str
    expiration_date: str
    hashed_card_number: str


def dict_to_config(data: dict) -> Config:
    return Config(
        ip_address=data.get("ip_address", ""),
        port=data.get("port", 0),
        send_rsp_before_timeout=data.get("send_rsp_before_timeout", False),
        card_issuer=data.get("card_issuer", ""),
        card_type=data.get("card_type", ""),
        card_number=data.get("card_number", ""),
        expiration_date=data.get("expiration_date", ""),
        hashed_card_number=data.get("hashed_card_number", "")
    )


def config_to_dict(config: Config) -> dict:
    return {
        'ip_address': config.ip_address,
        'port': config.port,
        'send_rsp_before_timeout': config.send_rsp_before_timeout,
        'card_issuer': config.card_issuer,
        'card_number': config.card_number,
        'card_type': config.card_type,
        'expiration_date': config.expiration_date,
        'hashed_card_number': config.hashed_card_number
    }


default_config_dict: dict = {
    'ip_address': '127.0.0.1',
    'port': 2605,
    'send_rsp_before_timeout': True,
    'card_issuer': 'VS',
    'card_type': 'CHIP',
    'card_number': '**********1234',
    'expiration_date': '2512',
    'hashed_card_number': '437B12A684A75C61235260',
}


def save_config(config: Config):
    dir = "data"
    filepath = f"{dir}/config.yaml"

    if not os.path.exists(dir):
        os.makedirs(dir)

    with open(filepath, "w") as file:
        yaml.dump(config_to_dict(config), file)
        print(f"INFO: Saved config to {filepath}")


def load_config() -> Config:
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
        config = dict_to_config(default_config_dict)
        save_config(config)
        return config

    print(f'INFO: Loaded config file "{filepath}"')

    original_keys = set(yaml_config.keys())
    for key, value in default_config_dict.items():
        yaml_config.setdefault(key, value)
    new_keys = set(yaml_config.keys()) - original_keys
    if new_keys:
        print(f'WARN: Keys "{new_keys}" are missing from "{filepath}", loading them from default config')
        save_config(dict_to_config(yaml_config))

    return dict_to_config(yaml_config)
