def get_config_dict(config_dict):
    return config_dict.get('flask', {})


def convert_to_flask_config_dict(config_dict, prefix):
    return {f"{prefix}_{k}".upper(): v for k, v in config_dict.items()}
