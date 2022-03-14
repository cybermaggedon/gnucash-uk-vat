
import json
from datetime import datetime

# Authentication object.  Supports loading from file as JSON, writing back
# updated auth, and refresh
class Auth:
    # Constructor, load auth from file
    def __init__(self, file="auth.json"):
        self.file = file
        try:
            self.auth = json.loads(open(file).read())
        except:
            self.auth = {}

    # Get an authentication data value
    def get(self, key):
        cfg = self.auth
        for v in key.split("."):
            cfg = cfg[v]
        return cfg

    # Write back to file
    def write(self):
        with open(self.file, "w") as auth_file:
            auth_file.write(json.dumps(self.auth, indent=4))

    # Refresh expired token using the refresh token, and write new
    # creds back to the auth file.  svc=API service
    async def refresh(self, svc):
        self.auth = await svc.refresh_token(self.auth["refresh_token"])
        self.write()

    # If token has expired, refresh.
    async def maybe_refresh(self, svc):
        if "expires" not in self.auth:
            raise RuntimeError("No token expiry.  Have you authenticated?")
        expires = datetime.fromisoformat(self.auth["expires"])
        if  datetime.utcnow() > expires:
            await self.refresh(svc)

