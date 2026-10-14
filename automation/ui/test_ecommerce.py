from playwright.sync_api import expect

def add(page):
 page.get_by_test_id('add-P1').click();expect(page.get_by_test_id('subtotal')).to_have_text('1000.00')
def test_add_product(page):
 add(page);expect(page.get_by_test_id('cart-items')).to_contain_text('P1')
def test_remove_product(page):
 add(page);page.get_by_test_id('remove-P1').click();expect(page.get_by_test_id('subtotal')).to_have_text('0.00')
def test_valid_coupon(page):
 add(page);page.get_by_test_id('coupon-input').fill('SAVE10');page.get_by_test_id('apply-coupon').click()
 expect(page.get_by_test_id('payable')).to_have_text('900.00')
def test_invalid_coupon(page):
 add(page);page.get_by_test_id('coupon-input').fill('INVALID');page.get_by_test_id('apply-coupon').click()
 expect(page.get_by_test_id('message')).to_have_text('Invalid coupon')
def test_checkout(page):
 add(page);page.get_by_test_id('checkout').click();expect(page.get_by_test_id('message')).to_have_text('Order ORDER-001 confirmed')
def test_empty_checkout(page):
 page.get_by_test_id('checkout').click();expect(page.get_by_test_id('message')).to_have_text('Empty cart')

def test_expired_coupon(page):
 add(page);page.get_by_test_id('coupon-input').fill('EXPIRED10');page.get_by_test_id('apply-coupon').click()
 expect(page.get_by_test_id('message')).to_have_text('Expired coupon')
