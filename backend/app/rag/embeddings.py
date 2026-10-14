import hashlib,math,os,re
import httpx
SYNONYMS={'promo':'coupon','voucher':'coupon','vouchers':'coupon','coupons':'coupon','basket':'cart','inventory':'stock','expired':'expiry','expires':'expiry','expiration':'expiry','redemption':'reuse','redeemed':'reuse','payable':'total','percentage':'discount','purchase':'checkout','items':'product','products':'product'}
STOP={'a','an','the','of','to','in','and','or','is','be','as','for','with','must','should','from','when','on','at','by','this','that','it','during','verify'}
def tokens(text):
 return [SYNONYMS.get(word,word) for word in re.findall(r'[a-z0-9]+',text.lower()) if word not in STOP]

class Embedder:
 def __init__(self):
  self.mode=os.getenv('QA_EMBEDDING_MODE','demo').lower()
  if self.mode not in ['demo','provider']:raise ValueError('Unknown embedding mode')
  self.model='hash-synonyms-v1' if self.mode=='demo' else os.getenv('QA_EMBEDDING_MODEL','')
  self.base=os.getenv('QA_EMBEDDING_BASE_URL','')
  if self.mode=='provider' and not all([self.model,self.base,os.getenv('QA_EMBEDDING_API_KEY')]):
   raise ValueError('Embedding provider configuration is incomplete')
  self.identity=hashlib.sha256((self.mode+'|'+self.model+'|'+self.base).encode()).hexdigest()[:16]
 def embed(self,texts):
  if self.mode=='provider':
   with httpx.Client(timeout=45) as client:
    response=client.post(self.base.rstrip('/')+'/embeddings',headers={'Authorization':'Bearer '+os.environ['QA_EMBEDDING_API_KEY']},json={'model':self.model,'input':texts})
    response.raise_for_status();rows=sorted(response.json()['data'],key=lambda row:row['index'])
   if [row['index'] for row in rows]!=list(range(len(texts))):raise ValueError('Incomplete embedding response')
   vectors=[row['embedding'] for row in rows]
  else:
   vectors=[]
   for text in texts:
    vector=[0.0]*384
    for word in tokens(text):
     index=int.from_bytes(hashlib.sha256(word.encode()).digest()[:4],'big')%384
     vector[index]+=1.0
    norm=math.sqrt(sum(value*value for value in vector)) or 1.0
    vectors.append([value/norm for value in vector])
  if not vectors or any(not row or any(not isinstance(value,(int,float)) or not math.isfinite(value) for value in row) for row in vectors) or len({len(row) for row in vectors})!=1:
   raise ValueError('Invalid embedding vectors')
  return vectors
