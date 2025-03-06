import os
from typing import Any
from langchain_openai import AzureChatOpenAI, AzureOpenAI, AzureOpenAIEmbeddings
from module.utils import config


azure_oai_credentials = config['production']['azure_oai_credentials']

os.environ["AZURE_OPENAI_API_KEY"] = azure_oai_credentials['AZURE_OPENAI_API_KEY']
os.environ["AZURE_OPENAI_ENDPOINT"] = azure_oai_credentials['AZURE_OPENAI_ENDPOINT']


class AzureOAI:
    """
    A wrapper class for initializing Azure OpenAI models based on the specified model type.

    Attributes:
        model_type (str): The type of model to initialize, either '3.5' or '4O'.

    Methods:
        __call__(): Returns an instance of the specified Azure OpenAI model.
        _initialize_embedding(): Initializes an Azure OpenAI embedding model.
        get_embedding(): Returns the embedding model instance.
    """

    def __init__(self, model_type: str) -> None:
        """
        Initializes the AzureOAI class with a specified model type.

        Args:
            model_type (str): The type of model to use, either '3.5' for instruct models
                              or '4O' for GPT-4o-based models.

        Raises:
            AssertionError: If the model_type is not '3.5' or '4O'.
        """
        assert model_type in ["3.5", "4O"], "model_type must be '3.5' or '4O'"
        self.model_type = model_type

    def __call__(self) -> Any:
        """
        Returns an instance of the selected Azure OpenAI model.

        Returns:
            AzureChatOpenAI or AzureOpenAI: An initialized model instance.

        Raises:
            KeyError: If the required API credentials are missing.
        """
        if self.model_type == "4O":
            llm_4o = AzureChatOpenAI(
                api_version=azure_oai_credentials["4O_API_VERSION"],
                azure_deployment=azure_oai_credentials["4O_AZURE_DEPLOYMENT"],
                model=azure_oai_credentials["4O_MODEL_NAME"],
                model_version=azure_oai_credentials["4O_MODEL_VERSION"],
                streaming=True
            )
            return llm_4o

        elif self.model_type == "3.5":
            llm = AzureOpenAI(
                model_name=azure_oai_credentials["MODEL_NAME"],
                api_version=azure_oai_credentials["API_VERSION"],
                azure_deployment=azure_oai_credentials["AZURE_DEPLOYMENT"],
                temperature=1,
                streaming=True
            )
            return llm

    def _initialize_embedding(self):
        """
        Initializes an Azure OpenAI embedding model.

        Returns:
            AzureOpenAIEmbeddings: An embedding model instance.
        """
        embedding = AzureOpenAIEmbeddings(
            azure_deployment=azure_oai_credentials["AZURE_EMBEDDING_DEPLOYMENT"],
            openai_api_version=azure_oai_credentials["AZURE_EMBEDDING_API_VERSION"]
        )
        return embedding

    def get_embedding(self):
        """
        Returns the embedding model instance.

        Returns:
            AzureOpenAIEmbeddings: The initialized embedding model.
        """
        return self.embedding
