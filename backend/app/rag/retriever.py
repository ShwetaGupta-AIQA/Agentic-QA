from ..telemetry import observe
import math
from .embeddings import tokens
from .vector_store import collection,LOCK

@observe('rag_search')
def search(request):
 store,embedder=collection()
 filters=[{'project':request.project}]
 if request.kind:filters.append({'kind':request.kind})
 if request.source_version:filters.append({'source_version':request.source_version})
 where=filters[0] if len(filters)==1 else {'$and':filters}
 with LOCK:
  if not store.count():return {'query':request.query,'sources':[],'embedding_mode':embedder.mode,'note':'Knowledge base is empty; ingest first'}
  response=store.query(query_embeddings=embedder.embed([request.query]),n_results=min(store.count(),max(30,request.top_k*5)),where=where,include=['documents','metadatas','distances'])
 query=set(tokens(request.query));ranked=[]
 for chunk,text,metadata,distance in zip(response['ids'][0],response['documents'][0],response['metadatas'][0],response['distances'][0]):
  overlap=query&set(tokens(metadata['title']+' '+text))
  lexical=len(overlap)/max(1,len(query))
  vector=max(0,min(1,1-distance))
  score=.75*lexical+.25*vector
  if embedder.mode=='demo' and not overlap:continue
  ranked.append({'source_id':metadata['source_id'],'citation_id':metadata['source_id']+'@'+metadata['source_version']+'#'+str(metadata['chunk_index']),'chunk_id':chunk,'title':metadata['title'],'text':text,'metadata':metadata,'score':round(score,4),'matched_terms':sorted(overlap)})
 ranked.sort(key=lambda row:(-row['score'],row['source_id'],row['chunk_id']))
 sources=[];seen=set()
 for row in ranked:
  identity=(row['source_id'],row['metadata']['source_version'])
  if identity not in seen:sources.append(row);seen.add(identity)
  if len(sources)>=request.top_k:break
 return {'query':request.query,'sources':sources,'embedding_mode':embedder.mode,'note':'Scores rank relevance and are not calibrated probabilities. Demo mode uses hashed lexical features with synonym normalization.'}


def get_source(source_id,project='commerce'):
 store,_=collection()
 with LOCK:
  rows=store.get(where={'$and':[{'source_id':source_id},{'project':project}]},include=['documents','metadatas'])
 if not rows['ids']:raise KeyError(source_id)
 results=[]
 for key,text,metadata in zip(rows['ids'],rows['documents'],rows['metadatas']):
  results.append({'source_id':source_id,'citation_id':source_id+'@'+metadata['source_version']+'#'+str(metadata['chunk_index']),
    'chunk_id':key,'title':metadata['title'],'text':text,'metadata':metadata,'score':None,'matched_terms':[]})
 return sorted(results,key=lambda row:row['metadata']['chunk_index'])
