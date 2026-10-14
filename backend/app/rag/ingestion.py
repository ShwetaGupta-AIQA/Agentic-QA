import argparse,hashlib,json,re
from pathlib import Path
from ..models.intelligence import Document
from .vector_store import collection,LOCK,ROOT

def chunks(text,size=800,overlap=120):
 if size<=overlap or overlap<0:raise ValueError('Invalid chunk size')
 return [text[index:index+size] for index in range(0,len(text),size-overlap) if text[index:index+size].strip()]

def ingest(documents):
 docs=[Document.model_validate(item) for item in documents]
 if not docs:raise ValueError('No knowledge documents supplied')
 if len({(doc.project,doc.id,doc.source_version) for doc in docs})!=len(docs):raise ValueError('Duplicate document identity in batch')
 store,embedder=collection();records=[]
 for doc in docs:
  for index,text in enumerate(chunks(doc.text)):
   digest=hashlib.sha256(text.encode()).hexdigest()
   key=hashlib.sha256((doc.project+'|'+doc.id+'|'+doc.source_version+'|'+str(index)).encode()).hexdigest()
   metadata={'source_id':doc.id,'title':doc.title,'project':doc.project,'kind':doc.kind,'source_version':doc.source_version,'requirement_id':doc.requirement_id,'test_id':doc.test_id,'synthetic':doc.synthetic,'chunk_index':index,'content_hash':digest,'document_hash':hashlib.sha256(json.dumps(doc.model_dump(),sort_keys=True).encode()).hexdigest()}
   records.append((key,text,metadata))
 with LOCK:
  existing=store.get(ids=[row[0] for row in records],include=['metadatas'])
  old=dict(zip(existing['ids'],existing['metadatas']))
  if any(row[0] in old and (old[row[0]]['content_hash']!=row[2]['content_hash'] or old[row[0]].get('document_hash',row[2]['document_hash'])!=row[2]['document_hash']) for row in records):
   raise ValueError('Source version is immutable; bump source_version before changing content')
  vectors=embedder.embed([row[1] for row in records])
  store.upsert(ids=[row[0] for row in records],documents=[row[1] for row in records],metadatas=[row[2] for row in records],embeddings=vectors)
 return {'documents':len(docs),'chunks':len(records),'indexed_chunks':store.count(),'embedding_mode':embedder.mode,'embedding_model':embedder.model}

def ingest_demo():
 return ingest(json.loads((ROOT/'data/knowledge/commerce.json').read_text(encoding='utf-8')))

def ingest_execution(record):
 if record['status'] in ['queued','running']:raise ValueError('Execution must finish before ingestion')
 docs=[]
 run_id=record['execution_id']
 docs.append({'id':'EXEC-'+run_id,'title':'Execution '+run_id,'text':json.dumps(record,indent=2),'kind':'execution','source_version':'execution-v1'})
 for index,row in enumerate(record.get('results',[])):
  docs.append({'id':f'LOG-{run_id}-{index}','title':row['test_id']+' '+row['name'],'text':json.dumps(row,indent=2),'kind':'log','source_version':'execution-v1','test_id':row['test_id']})
 return ingest(docs)

def ingest_workflow(record):
 if record.get('status')!='approved' or record.get('phase')!='ready_for_review':raise ValueError('Only approved complete workflows may be ingested')
 key=record['run_id']
 content=json.dumps({'requirement':record['requirement'],'analysis':record['analysis']})
 # Content-addressed revisions preserve provenance for subsequently edited cases.
 version=hashlib.sha256(json.dumps(record,sort_keys=True).encode()).hexdigest()[:12]
 docs=[{'id':'WORKFLOW-'+key,'title':'Approved requirement '+key,'text':content,'kind':'requirement','source_version':version,'requirement_id':key,'synthetic':False}]
 for case in record['test_cases']:
  docs.append({'id':key+'/'+case['id'],'title':case['title'],'text':json.dumps(case),'kind':'test','source_version':version,'requirement_id':key,'test_id':case['id'],'synthetic':False})
 return ingest(docs)

if __name__=='__main__':
 parser=argparse.ArgumentParser();parser.add_argument('--demo',action='store_true');args=parser.parse_args()
 if not args.demo:parser.error('Use --demo to ingest the checked-in synthetic corpus')
 print(json.dumps(ingest_demo(),indent=2))
