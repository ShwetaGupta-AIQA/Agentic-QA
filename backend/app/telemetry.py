"""Metadata-only telemetry. Never records bodies, URLs, credentials or exception text."""
import os,json,time,logging
from collections import Counter
from threading import RLock
from contextvars import ContextVar
from contextlib import contextmanager
from datetime import datetime,timezone
from uuid import uuid4
REQUEST=ContextVar('request_id',default=None);COUNTS=Counter();LOCK=RLock();LOGGER=logging.getLogger('qa.telemetry')
LOGGER.setLevel(logging.INFO)
if not LOGGER.handlers:LOGGER.addHandler(logging.StreamHandler())
LOGGER.propagate=False
ALLOWED={'event','request_id','span_id','parent_span_id','operation','duration_ms','status','error_kind','model','input_tokens','output_tokens','retry_count','evidence_count','tool_name'}
SPAN=ContextVar('span_id',default=None)
def emit(event,**metadata):
 data={k:v for k,v in metadata.items() if k in ALLOWED and isinstance(v,(str,int,float,bool,type(None)))}
 data.update(event=event,request_id=REQUEST.get(),timestamp=datetime.now(timezone.utc).isoformat())
 with LOCK:COUNTS[event]+=1
 LOGGER.info(json.dumps(data))
 if os.getenv('QA_LANGSMITH_ENABLED','false').lower()=='true':
  try:
   from langsmith import Client
   from datetime import timedelta
   # Upload only this sanitized completed metadata span; never auto-trace graph inputs.
   end=datetime.now(timezone.utc);client=Client(hide_inputs=True,hide_outputs=True)
   client.create_run(name=event,run_type='chain',inputs={},outputs={},id=uuid4(),start_time=end-timedelta(milliseconds=data.get('duration_ms',0)),end_time=end,extra={'metadata':data},project_name=os.getenv('LANGSMITH_PROJECT','agentic-qa-metadata'))
  except Exception:
   with LOCK:COUNTS['telemetry_export_failures']+=1
def metrics():
 with LOCK:return dict(COUNTS)
@contextmanager
def span(operation):
 start=time.monotonic();key=str(uuid4());parent=SPAN.get();token=SPAN.set(key);status='ok';kind=None
 try:yield
 except BaseException as exc:
  status='error';kind=type(exc).__name__
  if kind=='ValidationError':emit('validation_failure',operation=operation,error_kind=kind)
  raise
 finally:
  SPAN.reset(token);emit('span',operation=operation,span_id=key,parent_span_id=parent,duration_ms=round((time.monotonic()-start)*1000,3),status=status,error_kind=kind,retry_count=0)
def observe(operation):
 from functools import wraps
 def wrap(fn):
  @wraps(fn)
  def measured(*args,**kwargs):
   with span(operation):return fn(*args,**kwargs)
  return measured
 return wrap
