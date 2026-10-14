def add(api):return api.post('/cart',json={'product_id':'P1','quantity':1})
def test_valid_coupon(api):
 add(api);r=api.post('/coupon',json={'code':'SAVE10'})
 assert r.status_code==200;assert r.json()['payable']=='900.00'
def test_invalid_coupon(api):
 add(api);r=api.post('/coupon',json={'code':'INVALID'})
 assert r.status_code==400;assert r.json()['detail']=='Invalid coupon'
def test_expired_coupon(api):
 add(api);r=api.post('/coupon',json={'code':'EXPIRED10'})
 assert r.status_code==400, f'Expected expired coupon rejection, got {r.status_code}'
 assert r.json()['detail']=='Expired coupon'
def test_coupon_reuse(api):
 add(api);api.post('/coupon',json={'code':'SAVE10'});assert api.post('/checkout').status_code==200
 add(api);assert api.post('/coupon',json={'code':'SAVE10'}).status_code==409
def test_discount_calculation(api):
 api.post('/cart',json={'product_id':'P2','quantity':3});r=api.post('/coupon',json={'code':'SAVE10'}).json()
 assert (r['subtotal'],r['discount'],r['payable'])==('300.00','30.00','270.00')
def test_stock_exceeded(api):
 r=api.post('/cart',json={'product_id':'P1','quantity':6})
 assert r.status_code==409;assert api.get('/cart').json()['items']==[]
def test_exact_expiry(api):
 api.post('/fixtures/reset',json={'now':'2030-01-02T00:00:00Z'});add(api)
 assert api.post('/coupon',json={'code':'SAVE10'}).status_code==400
def test_before_expiry(api):
 api.post('/fixtures/reset',json={'now':'2030-01-01T23:59:59Z'});add(api)
 assert api.post('/coupon',json={'code':'SAVE10'}).status_code==200
