import hmac,os
def reviewer():return os.getenv('QA_RELEASE_REVIEWER','local-reviewer')
def authorize(header,name):
 secret=os.getenv('QA_RELEASE_REVIEW_TOKEN','')
 if len(secret)<32:raise PermissionError('Release reviewer credential is not configured')
 token=header[7:] if header and header.startswith('Bearer ') else ''
 if not token or not hmac.compare_digest(token.encode(),secret.encode()):raise PermissionError('Release reviewer credential is invalid')
 if name!=reviewer():raise PermissionError('Reviewer is not authorized')
