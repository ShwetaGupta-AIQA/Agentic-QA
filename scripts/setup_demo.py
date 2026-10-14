"""Create local ignored secrets once. Never echo credentials."""
import secrets,json
from pathlib import Path
import bcrypt
ROOT=Path(__file__).resolve().parents[1];directory=ROOT/'.secrets';directory.mkdir(exist_ok=True)
for name in ['db_password','api_token','reviewer_token']:
 path=directory/name
 if not path.exists():path.write_text(secrets.token_urlsafe(40)+'\n',newline='\n')
path=directory/'demo_htpasswd'
if not path.exists():
 password=secrets.token_urlsafe(32)
 path.write_text('qa:'+bcrypt.hashpw(password.encode(),bcrypt.gensalt()).decode()+'\n',newline='\n')
 (directory/'demo-login.json').write_text(json.dumps({'username':'qa','password':password},indent=2)+'\n')
print('Local demo secrets ready in .secrets; credentials were not printed. Login: .secrets/demo-login.json; reviewer: .secrets/reviewer_token')
