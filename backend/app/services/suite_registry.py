from pathlib import Path
ROOT=Path(__file__).resolve().parents[3]

def ui(name):return 'automation/ui/test_ecommerce.py::'+name
def api(name):return 'automation/api/test_ecommerce.py::'+name
REGISTRY={
 'ECOM-001':{'title':'Add available product to cart','nodes':[ui('test_add_product')]},
 'ECOM-002':{'title':'Remove product from cart','nodes':[ui('test_remove_product')]},
 'ECOM-003':{'title':'Apply valid ten-percent coupon','nodes':[ui('test_valid_coupon'),api('test_valid_coupon')]},
 'ECOM-004':{'title':'Reject invalid coupon','nodes':[ui('test_invalid_coupon'),api('test_invalid_coupon')]},
 'ECOM-005':{'title':'Reject expired coupon','nodes':[api('test_expired_coupon'),api('test_exact_expiry'),api('test_before_expiry'),ui('test_expired_coupon')]},
 'ECOM-006':{'title':'Reject coupon reuse','nodes':[api('test_coupon_reuse')]},
 'ECOM-007':{'title':'Verify discount calculation','nodes':[api('test_discount_calculation')]},
 'ECOM-008':{'title':'Reject quantity above stock','nodes':[api('test_stock_exceeded')]},
 'ECOM-009':{'title':'Complete checkout','nodes':[ui('test_checkout')]},
 'ECOM-010':{'title':'Reject empty checkout','nodes':[ui('test_empty_checkout')]},
}

def resolve(ids):
 if not ids or len(ids)!=len(set(ids)) or any(key not in REGISTRY for key in ids):
  raise ValueError('Select unique registered ECOM test IDs only')
 nodes=[node for key in ids for node in REGISTRY[key]['nodes']]
 for node in nodes:
  path=(ROOT/node.split('::')[0]).resolve()
  if not path.is_relative_to((ROOT/'automation').resolve()) or not path.is_file():
   raise ValueError('Registered suite is unavailable')
 return nodes

def catalog():
 return [{'id':key,'title':value['title'],'types':sorted({'UI' if '/ui/' in node else 'API' for node in value['nodes']}),
          'automation_count':len(value['nodes']),'contract_version':'commerce-v1'} for key,value in REGISTRY.items()]

def context_fingerprint():
 import hashlib,json
 files=['sut/ecommerce/app.py','sut/ecommerce/index.html','automation/conftest.py','automation/api/test_ecommerce.py','automation/ui/test_ecommerce.py']
 return hashlib.sha256(json.dumps(REGISTRY,sort_keys=True).encode()+b''.join((ROOT/name).read_bytes() for name in files)).hexdigest()
