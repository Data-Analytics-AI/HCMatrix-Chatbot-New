import os
import yaml
from dotenv import load_dotenv

# Load the .env file
load_dotenv()


# Load and resolve placeholders in the YAML file
def load_config_with_env(yaml_path):
    with open(yaml_path, 'r') as file:
        config = yaml.safe_load(file)

    # Recursively resolve placeholders
    def resolve_placeholders(obj):
        if isinstance(obj, dict):
            return {k: resolve_placeholders(v) for k, v in obj.items()}
        elif isinstance(obj, str) and obj.startswith("$"):
            return os.getenv(obj[1:], obj)  # Replace with env variable or keep original
        return obj

    return resolve_placeholders(config)


# Usage
config = load_config_with_env('config/config.yml')


# import os
# import yaml
# from dotenv import load_dotenv
#
# # Load the .env file
# load_dotenv()
#
# # Custom constructor to handle the !python/str tag
# def python_str_constructor(loader, node):
#     value = loader.construct_scalar(node)
#     return value  # Modify this if necessary for specific handling
#
# # Register the custom constructor for !python/str tag
# yaml.add_constructor('!python/str', python_str_constructor)
#
# # Load and resolve placeholders in the YAML file
# def load_config_with_env(yaml_path):
#     with open(yaml_path, 'r') as file:
#         config = yaml.load(file, Loader=yaml.FullLoader)
#
#     # Recursively resolve placeholders
#     def resolve_placeholders(obj):
#         if isinstance(obj, dict):
#             return {k: resolve_placeholders(v) for k, v in obj.items()}
#         elif isinstance(obj, str) and obj.startswith("$"):
#             return os.getenv(obj[1:], obj)  # Replace with env variable or keep original
#         return obj
#
#     return resolve_placeholders(config)
#
#
# # Usage
# config = load_config_with_env('config/config.yml')

