from zinolib.config.zino1 import ZinoV1Config


def get_config_dict(config_dict, section="default"):
    zino_dict = config_dict.get('zino', {})
    if not zino_dict or not 'connections' in zino_dict:
        return {}
    if zino_dict["connections"][section]:
        connection = zino_dict["connections"][section]
    else:
        return {}
    options = zino_dict.get("options", {})
    return {**connection, **options}


def make_zino1_config(config_dict, prefix='ZINO1'):
    zino_config_dict = {}
    if prefix and not prefix.endswith('_'):
        prefix = f"{prefix}_"
    for k, v in config_dict.copy().items():
        if not k.startswith(prefix):
            continue
        k = k[len(prefix):]
        k = k.lower()
        zino_config_dict[k] = v
    zino_config_dict["username"] = "fake"
    zino_config_dict["password"] = "fake"
    zino_config = ZinoV1Config(**zino_config_dict)
    zino_config.username = None
    zino_config.password = None
    return zino_config
