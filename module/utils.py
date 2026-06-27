import os
from pathlib import Path
import yaml
from dotenv import load_dotenv
import time
import asyncio
import functools
from azure.keyvault.secrets import SecretClient
from azure.identity import ClientSecretCredential

# Load the .env file
load_dotenv()


# Load and resolve placeholders in the YAML file
def load_config_with_env(yaml_path):
    """Loads a YAML configuration file and resolves placeholders with environment variables or Azure Key Vault secrets.

        Args:
            yaml_path (str or Path): The path to the YAML configuration file.

        Returns: dict: The resolved configuration dictionary with placeholders replaced by corresponding environment
        variables or secrets from Azure Key Vault.
    """
    with open(yaml_path, 'r') as file:
        config_file = yaml.safe_load(file)

    # Authenticate using ClientSecretCredential
    client_id = config_file['production']['adls_credentials']['client_id']
    tenant_id = config_file['production']['adls_credentials']['tenant_id']
    client_secret = os.getenv("CLIENT_SECRET")  # Only passed manually, NOT in Key Vault
    key_vault_name = os.getenv("KEY_VAULT_NAME")  # Set manually in env
    key_vault_url = f"https://{key_vault_name}.vault.azure.net"

    credential = ClientSecretCredential(tenant_id, client_id, client_secret)
    secret_client = SecretClient(vault_url=key_vault_url, credential=credential)

    # Recursively resolve placeholders
    def resolve_placeholders(obj):
        """Recursively resolves placeholders in the configuration file."""
        if isinstance(obj, dict):
            return {k: resolve_placeholders(v) for k, v in obj.items()}
        elif isinstance(obj, list):
            return [resolve_placeholders(item) for item in obj]
        elif isinstance(obj, str) and obj.startswith("$"):
            secret_name = obj[1:]

            # 1️⃣ First, check .env file
            env_value = os.getenv(secret_name)
            if env_value:
                return env_value  # Use .env value

            # 2️⃣ If not found in .env, check Key Vault
            try:
                secret_value = secret_client.get_secret(secret_name).value
                return secret_value
            except Exception:
                return obj  # Keep original if secret not found

        return obj
    return resolve_placeholders(config_file)


def timing_decorator(func):
    """Decorator to measure the execution time of a function, supporting both synchronous and asynchronous functions.

    Args:
        func (Callable): The function to be wrapped.

    Returns:
        Callable: The wrapped function with execution time measurement.
    """
    if asyncio.iscoroutinefunction(func):
        @functools.wraps(func)
        async def async_wrapper(*args, **kwargs):
            start_time = time.perf_counter()  # Start time
            result = await func(*args, **kwargs)  # Await async function
            end_time = time.perf_counter()  # End time
            execution_time = end_time - start_time
            print(f"⏳ {func.__name__} executed in {execution_time:.4f} seconds")
            return result
        return async_wrapper
    else:
        @functools.wraps(func)
        def sync_wrapper(*args, **kwargs):
            start_time = time.perf_counter()  # Start time
            result = func(*args, **kwargs)  # Run sync function
            end_time = time.perf_counter()  # End time
            execution_time = end_time - start_time
            print(f"⏳ {func.__name__} executed in {execution_time:.4f} seconds")
            return result
        return sync_wrapper


# Dynamically get the project root (HCMatrix-Chatbot)
PROJECT_ROOT = Path(__file__).resolve().parent.parent

# Define the config path
CONFIG_PATH = PROJECT_ROOT / "config" / "config.yml"

# Usage
config = load_config_with_env(CONFIG_PATH)
