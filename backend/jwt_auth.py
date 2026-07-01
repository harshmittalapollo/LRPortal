from jose import jwt
from datetime import datetime,timedelta

SECRET_KEY="LRSECRET123"

ALGORITHM="HS256"

def create_token(username):

    expire=datetime.utcnow()+timedelta(hours=24)

    data={

        "sub":username,
        "exp":expire

    }

    return jwt.encode(
        data,
        SECRET_KEY,
        algorithm=ALGORITHM
    )