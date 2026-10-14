import os
from pathlib import Path
from functools import lru_cache
from threading import RLock
import chromadb
from .embeddings import Embedder
ROOT=Path(__file__).resolve().parents[3]
LOCK=RLock()
@lru_cache(maxsize=8)
def client(path):
 if os.getenv('QA_CHROMA_HOST'):
  return chromadb.HttpClient(host=os.environ['QA_CHROMA_HOST'],port=int(os.getenv('QA_CHROMA_PORT','8000')),settings=chromadb.Settings(anonymized_telemetry=False))
 return chromadb.PersistentClient(path=path,settings=chromadb.Settings(anonymized_telemetry=False))
def collection():
 embedder=Embedder()
 path=str(Path(os.getenv('QA_KNOWLEDGE_PATH',str(ROOT/'.chroma'))).resolve())
 store=client(path).get_or_create_collection(name='qa-'+embedder.identity,embedding_function=None,metadata={'hnsw:space':'cosine','embedding_model':embedder.model,'embedding_mode':embedder.mode})
 return store,embedder
