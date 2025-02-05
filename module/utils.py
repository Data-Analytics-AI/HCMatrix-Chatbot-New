import os
import yaml
from dotenv import load_dotenv
import time

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


def timing_decorator(func):
    """Decorator to measure execution time of a function."""
    def wrapper(*args, **kwargs):
        start_time = time.perf_counter()  # Start time
        result = func(*args, **kwargs)    # Run the function
        end_time = time.perf_counter()    # End time
        execution_time = end_time - start_time
        print(f"⏳ {func.__name__} executed in {execution_time:.4f} seconds")
        return result  # Return original function output
    return wrapper



# Usage
config = load_config_with_env('config/config.yml')
