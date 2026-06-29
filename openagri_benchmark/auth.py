from uuid import uuid4
import datetime
import jwt

from openagri_benchmark.conf import (
    JWT_SIGNING_KEY,
    JWT_ALG,
)




def mocked_auth_token(user_id):
    payload = {
        'user_id': str(user_id),
        'exp': datetime.datetime.utcnow() + datetime.timedelta(days=1),
        'token_type': 'access',
        'jti': str(uuid4()),
    }
    token = jwt.encode(payload, JWT_SIGNING_KEY, algorithm=JWT_ALG)
    return token
