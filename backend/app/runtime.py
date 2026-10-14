"""Deployment secrets and fail-closed runtime validation."""
import os
from pathlib import Path
def load_secrets():
 for name in ['QA_API_TOKEN','QA_RELEASE_REVIEW_TOKEN','QA_DB_PASSWORD','LANGSMITH_API_KEY']:
  file=os.getenv(name+'_FILE')
  if file:os.environ[name]=Path(file).read_text().strip()
 if os.getenv('QA_DB_HOST'):
  from urllib.parse import quote
  os.environ['QA_DATABASE_URL']='postgresql://qa:'+quote(os.environ['QA_DB_PASSWORD'],safe='')+'@'+os.environ['QA_DB_HOST']+':5432/qa'
def controlled():return os.getenv('QA_DEPLOYMENT_MODE','local')=='controlled'
def validate():
 if not controlled():return
 if len(os.getenv('QA_API_TOKEN',''))<32 or len(os.getenv('QA_RELEASE_REVIEW_TOKEN',''))<32:raise RuntimeError('Controlled deployment requires access and reviewer credentials')
 if not os.getenv('QA_DATABASE_URL') or os.getenv('QA_EXECUTION_MODE')!='queue':raise RuntimeError('Controlled deployment requires PostgreSQL and isolated queue worker')
 if os.getenv('LANGSMITH_TRACING','false').lower()=='true':raise RuntimeError('Raw LangGraph tracing is disabled; use QA_LANGSMITH_ENABLED sanitized telemetry')
