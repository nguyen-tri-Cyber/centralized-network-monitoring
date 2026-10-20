"""Small JSON-RPC client; no third-party Python dependency."""

import json
from urllib import error, request


class ZabbixError(RuntimeError):
    pass


class ZabbixAPI:
    def __init__(self, base_url: str, timeout: int = 20):
        self.url = base_url.rstrip("/") + "/api_jsonrpc.php"
        self.timeout = timeout
        self.token = None
        self.request_id = 0

    def check_response(self, response: dict, method: str):
        if "error" in response:
            detail = response["error"]
            # Login errors must not echo any part of a credential.
            sensitive_methods = ("user.login", "user.update", "user.create", "host.create", "host.update")
            suffix = "" if method in sensitive_methods else f": {detail.get('data', '')}"
            raise ZabbixError(f"{method}: {detail.get('message', 'API error')}{suffix}")
        if "result" not in response:
            raise ZabbixError(f"{method}: response has no result")
        return response["result"]

    def call(self, method: str, params=None):
        self.request_id += 1
        body = json.dumps({"jsonrpc": "2.0", "method": method,
                           "params": {} if params is None else params,
                           "id": self.request_id}).encode("utf-8")
        headers = {"Content-Type": "application/json-rpc"}
        if self.token and method not in ("apiinfo.version", "user.login"):
            headers["Authorization"] = f"Bearer {self.token}"
        req = request.Request(self.url, data=body, headers=headers, method="POST")
        try:
            with request.urlopen(req, timeout=self.timeout) as response:
                payload = json.load(response)
        except (error.URLError, TimeoutError, OSError, ValueError) as exc:
            raise ZabbixError(f"{method}: cannot reach or decode Zabbix API ({type(exc).__name__})") from exc
        return self.check_response(payload, method)

    def login(self, username: str, password: str):
        self.token = self.call("user.login", {"username": username, "password": password})
        return self.token

    def logout(self):
        if self.token:
            try:
                self.call("user.logout")
            finally:
                self.token = None
