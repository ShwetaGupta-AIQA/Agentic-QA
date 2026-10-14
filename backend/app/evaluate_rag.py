import argparse,json,os
from pathlib import Path
from .models.intelligence import SearchRequest
from .rag.retriever import search,get_source
from .rag.ingestion import ingest_demo
from .rag.vector_store import ROOT

def evaluate():
 if os.getenv('QA_EMBEDDING_MODE','demo')!='demo':raise ValueError('This labeled baseline evaluation requires demo embeddings')
 ingest_demo()
 dataset=json.loads((ROOT/'data/evaluation/rag_queries.json').read_text(encoding='utf-8'));rows=[];verified=0;references=0
 for sample in dataset:
  result=search(SearchRequest(query=sample['query'],kind=sample['kind'],top_k=5))
  references+=len(result['sources'])
  verified+=sum(any(stored['citation_id']==hit['citation_id'] for stored in get_source(hit['source_id'])) for hit in result['sources'])
  found={hit['source_id'] for hit in result['sources']};relevant=set(sample['relevant_ids']);correct=len(found&relevant)
  rows.append({'id':sample['id'],'query':sample['query'],'retrieved_ids':sorted(found),'relevant_ids':sorted(relevant),'recall_at_5':correct/len(relevant),'precision_at_5':correct/5})
 return {'dataset':'commerce-rag-v1','embedding_mode':'demo','queries':len(rows),'mean_recall_at_5':sum(row['recall_at_5'] for row in rows)/len(rows),
  'mean_precision_at_5':sum(row['precision_at_5'] for row in rows)/len(rows),'source_reference_percent':100*verified/references if references else 0,
  'scope':'12 synthetic labeled queries in a small checked-in corpus, deterministic hashed lexical/synonym embeddings. Not learned semantic model quality or production generalization. Precision denominator is five, including empty slots.',
  'results':rows}

if __name__=='__main__':
 parser=argparse.ArgumentParser();parser.add_argument('--output');args=parser.parse_args();report=evaluate();text=json.dumps(report,indent=2)
 if args.output:Path(args.output).write_text(text+'\n',encoding='utf-8')
 print(text)
