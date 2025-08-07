
import json
from datetime import datetime, timezone
from typing import Dict, Any

# Authentication object.  Supports loading from file as JSON, writing back
# updated auth, and refresh
class Auth:
    file: str
    auth: Dict[str, Any]
    
    # Constructor, load auth from file
    def __init__(self, file: str = "auth.json") -> None:
        self.file = file
        try:
            self.auth = json.loads(open(file).read())
        except:
            self.auth = {}

    # Get an authentication data value
    def get(self, key: str) -> Any:
        cfg = self.auth
        for v in key.split("."):
            cfg = cfg[v]
        return cfg

    # Write back to file
    def write(self) -> None:
        with open(self.file, "w") as auth_file:
            auth_file.write(json.dumps(self.auth, indent=4))

    # Refresh expired token using the refresh token, and write new
    # creds back to the auth file.  svc=API service
    async def refresh(self, svc: Any) -> None:
        self.auth = await svc.refresh_token(self.auth["refresh_token"])
        self.write()

    # If token has expired, refresh.
    async def maybe_refresh(self, svc: Any) -> None:
        if "expires" not in self.auth:
            raise RuntimeError("No token expiry.  Have you authenticated?")
        expires = datetime.fromisoformat(self.auth["expires"])
        expires = expires.replace(tzinfo=timezone.utc)
        if  datetime.now(timezone.utc) > expires:
            await self.refresh(svc)

