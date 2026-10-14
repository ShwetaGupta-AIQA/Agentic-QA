import os,hmac,time
from uuid import uuid4
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse
from .runtime import controlled
from .telemetry import REQUEST,emit
class AccessTelemetryMiddleware(BaseHTTPMiddleware):
 async def dispatch(self,request,call_next):
  key=str(uuid4());token=REQUEST.set(key);started=time.monotonic();status=500
  try:
   if controlled() and request.url.path!='/health':
    expected=os.getenv('QA_API_TOKEN','');provided=request.headers.get('X-QA-Access-Token','')
    if len(expected)<32 or not hmac.compare_digest(expected.encode(),provided.encode()):
     emit('access_denied');status=401;return JSONResponse({'detail':'Demo access credential required'},401)
    if request.method!='GET' and request.url.path.startswith('/healing'):
     status=403;return JSONResponse({'detail':'Self-healing browser operations are local-only; deployment exposes isolated registered execution jobs'},403)
   response=await call_next(request);status=response.status_code;response.headers['X-Request-ID']=key
   response.headers['X-Content-Type-Options']='nosniff';return response
  finally:
   route=request.scope.get('route');emit('http_request',operation=getattr(route,'path','unmatched'),status=status,duration_ms=round((time.monotonic()-started)*1000,3));REQUEST.reset(token)
