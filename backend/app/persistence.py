"""Lazy durable graph compilation; memory remains the local/test default."""
import os
from contextlib import ExitStack
from threading import RLock
from langgraph.checkpoint.memory import MemorySaver
STACK=ExitStack();LOCK=RLock();SAVERS={}
def saver():
 url=os.getenv('QA_DATABASE_URL','')
 with LOCK:
  if url not in SAVERS:
   if url:
    from psycopg_pool import ConnectionPool
    from psycopg.rows import dict_row
    from langgraph.checkpoint.postgres import PostgresSaver
    from langgraph.checkpoint.serde.jsonplus import JsonPlusSerializer
    pool=STACK.enter_context(ConnectionPool(url,min_size=1,max_size=4,kwargs={'autocommit':True,'row_factory':dict_row},timeout=10))
    pool.wait(timeout=15)
    item=PostgresSaver(pool,serde=JsonPlusSerializer(allowed_msgpack_modules=[]));item.setup()
   else:item=MemorySaver()
   SAVERS[url]=item
  return SAVERS[url]
def close():
 with LOCK:STACK.close();SAVERS.clear()
class DurableGraph:
 def __init__(self,builder):self.builder=builder;self.graphs={}
 def __getattr__(self,name):
  item=saver();key=id(item)
  with LOCK:
   if key not in self.graphs:self.graphs[key]=self.builder.compile(checkpointer=item)
   graph=self.graphs[key]
  return getattr(graph,name)
