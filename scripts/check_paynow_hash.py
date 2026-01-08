import os
import hashlib
import hmac
from urllib.parse import unquote_plus

# Load env
from pathlib import Path
BASE = Path(__file__).resolve().parent.parent
env_file = BASE / '.env'
env = {}
if env_file.exists():
    for line in env_file.read_text().splitlines():
        if '=' in line and not line.strip().startswith('#'):
            k,v = line.split('=',1)
            env[k.strip()] = v.strip().strip("'\"")

KEY = env.get('PAYNOW_INTEGRATION_KEY','')
print('Using key:', KEY[:8] + '...' if KEY else '(none)')

# Example raw body from logs
raw = b'reference=f1895f26-97c0-4d47-9cbe-ef9cda1fc395&paynowreference=35216224&amount=1324.50&status=Awaiting+Delivery&pollurl=https%3a%2f%2fwww.paynow.co.zw%2fInterface%2fCheckPayment%2f%3fguid%3de88e691a-8791-4eff-9c2b-721a485942d7&hash=03DE7C4204F0A102CA76D6AD0ED435866EEC30DF0FE3A3674D1D4BB905670BC2BB94F7C2AE014D791C688B1A6F02D18778F115C371D53F9AD86DC8298E9B22BA'

# simulate parse
s = raw
# find hash param
try:
    idx = s.lower().find(b'&hash=')
    if idx != -1:
        body_no_hash = s[:idx]
        incoming_hash = s[idx+6:].decode('utf-8').strip().lower()
    else:
        body_no_hash = s
        incoming_hash = None
except Exception as e:
    print('parse error',e)
    raise

print('incoming_hash=', incoming_hash[:64] if incoming_hash else None)

key = KEY.encode('utf-8')

candidates = {}

# HMAC-SHA256 over raw
candidates['hmac_sha256_raw'] = hmac.new(key, s, hashlib.sha256).hexdigest()
# HMAC-SHA512 over raw
candidates['hmac_sha512_raw'] = hmac.new(key, s, hashlib.sha512).hexdigest()
# HMAC-SHA512 over raw_no_hash
candidates['hmac_sha512_raw_no_hash'] = hmac.new(key, body_no_hash, hashlib.sha512).hexdigest()
# HMAC-SHA256 over raw_no_hash
candidates['hmac_sha256_raw_no_hash'] = hmac.new(key, body_no_hash, hashlib.sha256).hexdigest()
# SHA512 of raw+key
candidates['sha512_raw_key'] = hashlib.sha512(s + key).hexdigest()
# SHA512 of key+raw
candidates['sha512_key_raw'] = hashlib.sha512(key + s).hexdigest()
# SHA512 of url-decoded body_no_hash
try:
    decoded = unquote_plus(body_no_hash.decode('utf-8'))
    candidates['hmac_sha512_decoded'] = hmac.new(key, decoded.encode('utf-8'), hashlib.sha512).hexdigest()
    candidates['sha512_decoded_key_end'] = hashlib.sha512((decoded + KEY).encode('utf-8')).hexdigest()
except Exception as e:
    candidates['hmac_sha512_decoded'] = None

# concat fields
from urllib.parse import parse_qs
qs = parse_qs(body_no_hash.decode('utf-8'))
ref = qs.get('reference',[''])[0]
payref = qs.get('paynowreference',[''])[0]
amount = qs.get('amount',[''])[0]
status = qs.get('status',[''])[0]
pollurl = qs.get('pollurl',[''])[0]
concat = f"{ref}{payref}{amount}{status}{pollurl}{KEY}"
candidates['sha512_concat_end_key'] = hashlib.sha512(concat.encode('utf-8')).hexdigest()
concat2 = f"{KEY}{ref}{payref}{amount}{status}{pollurl}"
candidates['sha512_concat_start_key'] = hashlib.sha512(concat2.encode('utf-8')).hexdigest()
concat_low = f"{ref}{payref}{amount}{status.lower()}{pollurl}{KEY}"
candidates['sha512_concat_status_lower'] = hashlib.sha512(concat_low.encode('utf-8')).hexdigest()

# print first 6 candidates
for k,v in candidates.items():
    print(k, v[:64])

if incoming_hash:
    for k,v in candidates.items():
        if v and v.lower() == incoming_hash:
            print('MATCH', k)
            break
    else:
        print('No match found')
else:
    print('No incoming hash to check')
