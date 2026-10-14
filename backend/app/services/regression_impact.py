from ..models.intelligence import SearchRequest
from ..rag.retriever import search
from .suite_registry import REGISTRY

def analyze(request):
 filters=request.model_copy(update={'kind':'test','top_k':10})
 retrieval=search(filters);impacts=[];seen=set()
 for source in retrieval['sources']:
  key=source['metadata']['test_id']
  if not key or key in seen:continue
  seen.add(key)
  impacts.append({'test_id':key,'title':source['title'],'priority':'high' if source['score']>=.5 else 'medium',
    'reason':'Relevant retrieved test context; shared terms: '+', '.join(source['matched_terms']),
    'citation_ids':[source['citation_id']],'registered_automation':key in REGISTRY,'needs_review':True})
 return {'change':request.query,'impacted_tests':impacts,'sources':retrieval['sources'],
   'embedding_mode':retrieval['embedding_mode'],'note':'Potential impact ranked by retrieval relevance, not proven dependency analysis. No tests are automatically selected or executed.'}
