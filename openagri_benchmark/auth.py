from uuid import uuid4
import datetime
import jwt

from openagri_benchmark.conf import (
    JWT_SIGNING_KEY,
    JWT_ALG,
)




def mocked_auth_token(user_id):
    payload = {
        "token_type": "access",
        "exp": datetime.datetime.utcnow() + datetime.timedelta(days=1),
        "iat": datetime.datetime.utcnow(),
        "jti": "ea30e26cf67247aa98609598dc418920",
        "user_id": str(uuid4()),
        "username": "admin",
        "first_name": "",
        "last_name": "",
        "uuid": "62ec99cd-1e5d-4bf3-845a-5aa33d4402b0",
        "rjti": "ee3ff1d85f5b44d09a3aa04f4b56d795",
    }
    token = jwt.encode(payload, JWT_SIGNING_KEY, algorithm=JWT_ALG)
    return token
