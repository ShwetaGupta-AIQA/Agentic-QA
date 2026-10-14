"""Private single-job execution worker; no listening HTTP port or provider credentials."""
import time,signal
from pathlib import Path
from .runtime import load_secrets
load_secrets()
from .services import job_queue,execution_service as execution
STOP=False
def stop(*args):
 global STOP;STOP=True
def main():
 signal.signal(signal.SIGTERM,stop);signal.signal(signal.SIGINT,stop);job_queue.setup()
 while not STOP:
  Path('/tmp/qa-worker-heartbeat').touch()
  row=job_queue.claim()
  if row:
   key=str(row['id']);record=execution.get(key)
   if record['approved'] is not True or record['test_ids']!=row['test_ids']:raise RuntimeError('Job approval evidence mismatch')
   execution.execute(key,row['test_ids'],release_slot=False);job_queue.finish(key)
  else:time.sleep(1)
if __name__=='__main__':main()
