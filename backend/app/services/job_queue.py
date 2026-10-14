"""Bounded PostgreSQL jobs, atomic lease; expired work requires explicit rerun."""
import os,json
from uuid import UUID
def connect():
 import psycopg
 from psycopg.rows import dict_row
 return psycopg.connect(os.environ['QA_DATABASE_URL'],row_factory=dict_row,connect_timeout=10)
def setup():
 with connect() as c:
  c.execute("SELECT pg_advisory_xact_lock(834709)")
  c.execute("CREATE TABLE IF NOT EXISTS qa_jobs (id UUID PRIMARY KEY, test_ids JSONB NOT NULL, state TEXT NOT NULL DEFAULT 'queued', created_at TIMESTAMPTZ NOT NULL DEFAULT now(), lease_until TIMESTAMPTZ, finished_at TIMESTAMPTZ)")
def enqueue(key,ids):
 with connect() as c:
  c.execute("SELECT pg_advisory_xact_lock(834708)")
  count=c.execute("SELECT count(*) AS n FROM qa_jobs WHERE state IN ('queued','running')").fetchone()['n']
  if count>=4:raise RuntimeError('Execution queue is full')
  c.execute('INSERT INTO qa_jobs(id,test_ids) VALUES (%s,%s::jsonb)',(str(UUID(key)),json.dumps(ids)))
def claim():
 with connect() as c:
  c.execute("UPDATE qa_jobs SET state='error',finished_at=now() WHERE state='running' AND lease_until<now()")
  row=c.execute("SELECT * FROM qa_jobs WHERE state='queued' ORDER BY created_at FOR UPDATE SKIP LOCKED LIMIT 1").fetchone()
  if row:c.execute("UPDATE qa_jobs SET state='running',lease_until=now()+interval '240 seconds' WHERE id=%s",(row['id'],))
  return row
def finish(key):
 with connect() as c:c.execute("UPDATE qa_jobs SET state='finished',finished_at=now() WHERE id=%s AND state='running'",(str(UUID(key)),))
def state(key):
 with connect() as c:
  c.execute("UPDATE qa_jobs SET state='error',finished_at=now() WHERE state='running' AND lease_until<now()")
  row=c.execute('SELECT state FROM qa_jobs WHERE id=%s',(str(UUID(key)),)).fetchone()
  return row['state'] if row else None
