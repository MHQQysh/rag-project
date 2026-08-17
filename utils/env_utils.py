import os

from dotenv import load_dotenv

load_dotenv(override=True)

OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')
DEEPSEEK_API_KEY = os.getenv('DEEPSEEK_API_KEY')

MILVUS_URI = os.getenv('MILVUS_URI', 'http://127.0.0.1:19530')

COLLECTION_NAME = os.getenv('MILVUS_COLLECTION_NAME', 't_collection01')
