from datetime import datetime, timezone
from decimal import Decimal, ROUND_HALF_UP
from threading import RLock
from pathlib import Path
from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel, ConfigDict, Field

app=FastAPI(title='Synthetic Commerce SUT',version='1.0')
lock=RLock()
PRODUCTS={'P1':{'id':'P1','name':'QA Notebook','price':'1000.00','stock':5},'P2':{'id':'P2','name':'Test Pen','price':'100.00','stock':10}}
state={}

def reset(now='2030-01-01T12:00:00Z', defect=False):
 with lock:
  state.clear();state.update(products={key:dict(value) for key,value in PRODUCTS.items()},cart={},coupon=None,used=[],orders=[],now=now,defect=defect)
reset()

class Strict(BaseModel):
 model_config=ConfigDict(extra='forbid',strict=True)
class CartInput(Strict):
 product_id:str
 quantity:int=Field(ge=1,le=100)
class CouponInput(Strict):
 code:str=Field(min_length=1,max_length=50)
class ResetInput(Strict):
 now:str='2030-01-01T12:00:00Z'
 defect:bool=False

def cart():
 subtotal=sum(Decimal(state['products'][key]['price'])*quantity for key,quantity in state['cart'].items())
 discount=(subtotal*Decimal('.10')).quantize(Decimal('.01'),rounding=ROUND_HALF_UP) if state['coupon'] else Decimal(0)
 return {'items':[{'product_id':key,'quantity':quantity} for key,quantity in state['cart'].items()],
   'subtotal':f'{subtotal:.2f}','discount':f'{discount:.2f}','payable':f'{max(Decimal(0),subtotal-discount):.2f}','coupon':state['coupon']}

def validate_coupon(code):
 if code not in ['SAVE10','EXPIRED10']:raise HTTPException(400,'Invalid coupon')
 if code in state['used']:raise HTTPException(409,'Coupon already redeemed')
 expiry='2029-01-01T00:00:00Z' if code=='EXPIRED10' else '2030-01-02T00:00:00Z'
 if not state['defect'] and datetime.fromisoformat(state['now'].replace('Z','+00:00'))>=datetime.fromisoformat(expiry.replace('Z','+00:00')):
  raise HTTPException(400,'Expired coupon')
 if not state['cart']:raise HTTPException(400,'Empty cart')

@app.get('/')
def index():return FileResponse(Path(__file__).with_name('index.html'))
@app.get('/health')
def health():return {'status':'ok'}
@app.get('/products')
def products():return list(state['products'].values())
@app.get('/cart')
def get_cart():
 with lock:return cart()
@app.post('/cart')
def add(body:CartInput):
 with lock:
  if body.product_id not in state['products']:raise HTTPException(404,'Unknown product')
  quantity=state['cart'].get(body.product_id,0)+body.quantity
  if quantity>state['products'][body.product_id]['stock']:raise HTTPException(409,'Insufficient stock')
  state['cart'][body.product_id]=quantity
  return cart()
@app.delete('/cart/{product_id}')
def remove(product_id:str):
 with lock:
  state['cart'].pop(product_id,None)
  if not state['cart']:state['coupon']=None
  return cart()
@app.post('/coupon')
def coupon(body:CouponInput):
 with lock:
  validate_coupon(body.code);state['coupon']=body.code
  return cart()
@app.post('/checkout')
def checkout():
 with lock:
  if not state['cart']:raise HTTPException(400,'Empty cart')
  if state['coupon']:validate_coupon(state['coupon'])
  for key,quantity in state['cart'].items():
   if quantity>state['products'][key]['stock']:raise HTTPException(409,'Insufficient stock')
  order={'id':f'ORDER-{len(state["orders"])+1:03}',**cart()}
  for key,quantity in state['cart'].items():state['products'][key]['stock']-=quantity
  if state['coupon']:state['used'].append(state['coupon'])
  state['orders'].append(order);state['cart']={};state['coupon']=None
  return order
@app.post('/fixtures/reset')
def reset_fixture(body:ResetInput):
 try:
  parsed=datetime.fromisoformat(body.now.replace('Z','+00:00'))
  if parsed.tzinfo is None:raise ValueError('Timezone required')
 except ValueError:raise HTTPException(422,'ISO timestamp with timezone required')
 # Known-defect injection is for controlled local evidence checks only.
 reset(body.now,body.defect);return {'status':'reset','customer_id':'synthetic-customer-001'}
