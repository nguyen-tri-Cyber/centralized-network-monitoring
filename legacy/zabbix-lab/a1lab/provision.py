"""Idempotent Zabbix lab configuration."""

import json
import secrets
from pathlib import Path

from .api import ZabbixError


DASHBOARD_NAME = "A1 Lab - Tong quan"
ACTION_NAME = "A1 Lab - Email su co"
MEDIA_NAME = "A1 Lab Mailpit"
MAP_NAME = "A1 Lab - Logical host map"
ACCOUNTS_FILE = "local-accounts.json"


def read_settings(project_dir: Path) -> dict:
    settings = {}
    for line in (project_dir / ".env").read_text(encoding="utf-8-sig").splitlines():
        if line and not line.startswith("#") and "=" in line:
            key, value = line.split("=", 1)
            settings[key] = value
    for key in ("SNMP_COMMUNITY", "LAB_ENDPOINT_IP"):
        if not settings.get(key):
            raise ValueError(f"Missing {key} in .env; run setup.ps1 first")
    return settings


def single(api, method: str, field: str, value: str, output=None):
    params = {"output": output or "extend", "filter": {field: [value]}}
    rows = api.call(method, params)
    if len(rows) > 1:
        raise ZabbixError(f"{method}: duplicate {field}={value}")
    return rows[0] if rows else None


def template_id(api, name: str) -> str:
    item = single(api, "template.get", "name", name, ["templateid", "name"])
    if not item:
        raise ZabbixError(f"Missing built-in template: {name}")
    return item["templateid"]


def ensure_host_group(api) -> str:
    group = single(api, "hostgroup.get", "name", "A1 Lab", ["groupid", "name"])
    return group["groupid"] if group else api.call("hostgroup.create", {"name": "A1 Lab"})["groupids"][0]


def host_definitions(group_id: str, settings: dict, templates: dict):
    group = [{"groupid": group_id}]
    return [
        {"host": "A1-LAB-ENDPOINT", "name": "A1 Lab - ICMP endpoint", "groups": group,
         "templates": [{"templateid": templates["ICMP Ping"]}],
         "interfaces": [{"type": 1, "main": 1, "useip": 1, "ip": settings["LAB_ENDPOINT_IP"],
                         "dns": "", "port": "10050"}]},
        {"host": "lab-linux-agent", "name": "A1 Lab - Linux agent container", "groups": group,
         "templates": [{"templateid": templates["Linux by Zabbix agent"]}],
         "interfaces": [{"type": 1, "main": 1, "useip": 0, "ip": "", "dns": "lab-agent", "port": "10050"}]},
        {"host": "A1-LAB-SNMP", "name": "A1 Lab - SNMP container", "groups": group,
         "templates": [{"templateid": templates["Network Generic Device by SNMP"]}],
         "interfaces": [{"type": 2, "main": 1, "useip": 0, "ip": "", "dns": "lab-snmp", "port": "161",
                         "details": {"version": 2, "bulk": 1, "community": "{$SNMP_COMMUNITY}"}}],
         "macros": [{"macro": "{$SNMP_COMMUNITY}", "value": settings["SNMP_COMMUNITY"]}]},
    ]


def ensure_hosts(api, group_id: str, settings: dict) -> dict:
    names = ("ICMP Ping", "Linux by Zabbix agent", "Network Generic Device by SNMP")
    templates = {name: template_id(api, name) for name in names}
    ids = {}
    for definition in host_definitions(group_id, settings, templates):
        name = definition["host"]
        host = single(api, "host.get", "host", name, ["hostid", "host"])
        ids[name] = host["hostid"] if host else api.call("host.create", definition)["hostids"][0]
    return ids


def ensure_zone_groups(api, root_id: str, hosts: dict) -> dict:
    zones = {}
    for zone_name in ("A1 Lab/Zone A", "A1 Lab/Zone B"):
        group = single(api, "hostgroup.get", "name", zone_name, ["groupid", "name"])
        zones[zone_name] = group["groupid"] if group else api.call("hostgroup.create", {"name": zone_name})["groupids"][0]
    assignments = {"A1-LAB-ENDPOINT": "A1 Lab/Zone A", "A1-LAB-SNMP": "A1 Lab/Zone A",
                   "lab-linux-agent": "A1 Lab/Zone B"}
    for host_name, zone_name in assignments.items():
        host_id = hosts[host_name]
        rows = api.call("host.get", {"hostids": host_id, "output": ["hostid"],
            "selectHostGroups": ["groupid"]})
        existing = {row["groupid"] for row in rows[0]["hostgroups"]}
        wanted = existing | {root_id, zones[zone_name]}
        if wanted != existing:
            api.call("host.update", {"hostid": host_id,
                                     "groups": [{"groupid": gid} for gid in sorted(wanted)]})
    return zones


def disk_item_definition(host_id: str, interface_id: str) -> dict:
    return {"hostid": host_id, "interfaceid": interface_id,
            "name": "A1 Lab: root filesystem used", "type": 0,
            "key_": "vfs.fs.size[/,pused]", "value_type": 0, "delay": "1m", "units": "%"}


def ensure_disk_item(api, host_id: str) -> str:
    key = "vfs.fs.size[/,pused]"
    rows = api.call("item.get", {"hostids": host_id, "output": ["itemid", "key_"],
                                 "filter": {"key_": [key]}})
    if rows:
        return rows[0]["itemid"]
    interfaces = api.call("hostinterface.get", {"hostids": host_id,
                                               "output": ["interfaceid", "type"]})
    agent = next((row for row in interfaces if str(row["type"]) == "1"), None)
    if not agent:
        raise ZabbixError("Linux agent host has no Agent interface")
    return api.call("item.create", disk_item_definition(host_id, agent["interfaceid"]))["itemids"][0]


def latency_trigger_definition() -> dict:
    return {"description": "A1 Lab: ICMP latency above 200 ms (2 checks)",
            "expression": "min(/A1-LAB-ENDPOINT/icmppingsec,#2)>0.2",
            "priority": 2, "status": 0,
            "tags": [{"tag": "A1Lab", "value": "latency"}]}


def ensure_latency_trigger(api, host_id: str) -> str:
    definition = latency_trigger_definition()
    rows = api.call("trigger.get", {"hostids": host_id,
                                    "output": ["triggerid", "description"],
                                    "filter": {"description": [definition["description"]]}})
    if rows:
        return rows[0]["triggerid"]
    return api.call("trigger.create", definition)["triggerids"][0]


def ensure_media_type(api) -> str:
    config = {
        "type": 0, "name": MEDIA_NAME, "provider": 0, "smtp_server": "mailpit",
        "smtp_port": 1025, "smtp_helo": "a1-lab.local", "smtp_email": "a1-lab@example.test",
        "smtp_security": 0, "smtp_authentication": 0, "status": 0,
        "message_templates": [
            {"eventsource": 0, "recovery": 0, "subject": "A1 LAB PROBLEM: {EVENT.NAME}",
             "message": "Host: {HOST.NAME}\nEvent: {EVENT.NAME}\nAt: {EVENT.DATE} {EVENT.TIME}\nID: {EVENT.ID}"},
            {"eventsource": 0, "recovery": 1, "subject": "A1 LAB RECOVERY: {EVENT.NAME}",
             "message": "Host: {HOST.NAME}\nRecovered: {EVENT.RECOVERY.DATE} {EVENT.RECOVERY.TIME}\nID: {EVENT.ID}"},
        ],
    }
    existing = single(api, "mediatype.get", "name", MEDIA_NAME, ["mediatypeid", "name"])
    if existing:
        api.call("mediatype.update", {"mediatypeid": existing["mediatypeid"], **{k: v for k, v in config.items() if k != "type"}})
        return existing["mediatypeid"]
    return api.call("mediatype.create", config)["mediatypeids"][0]


def ensure_user_group(api, name: str, host_group_id: str, permission: int) -> str:
    group = single(api, "usergroup.get", "name", name, ["usrgrpid", "name"])
    rights = [{"id": host_group_id, "permission": permission}]
    if group:
        api.call("usergroup.update", {"usrgrpid": group["usrgrpid"], "hostgroup_rights": rights})
        return group["usrgrpid"]
    return api.call("usergroup.create", {"name": name, "hostgroup_rights": rights})["usrgrpids"][0]


def load_accounts(project_dir: Path) -> dict:
    path = project_dir / ACCOUNTS_FILE
    accounts = json.loads(path.read_text(encoding="utf-8")) if path.exists() else {}
    changed = False
    for username in ("a1-operator", "a1-viewer"):
        if username not in accounts:
            accounts[username] = secrets.token_urlsafe(24)
            changed = True
    if changed:
        path.write_text(json.dumps(accounts, indent=2) + "\n", encoding="utf-8")
    return accounts


def ensure_users(api, project_dir: Path, operator_group_id: str, viewer_group_id: str,
                 media_type_id: str) -> dict:
    roles = api.call("role.get", {"output": ["roleid", "name", "type"]})
    role = next((row for row in roles if row["name"] == "User role"), None)
    if not role:
        role = next((row for row in roles if str(row["type"]) == "1"), None)
    if not role:
        raise ZabbixError("No Zabbix User role found")
    accounts = load_accounts(project_dir)
    users = {}
    for username, group_id in (("a1-operator", operator_group_id), ("a1-viewer", viewer_group_id)):
        existing = single(api, "user.get", "username", username, ["userid", "username"])
        if existing:
            users[username] = existing["userid"]
            continue
        params = {"username": username, "passwd": accounts[username], "roleid": role["roleid"],
                  "usrgrps": [{"usrgrpid": group_id}]}
        if username == "a1-operator":
            params["medias"] = [{"mediatypeid": media_type_id, "sendto": ["operator@example.test"],
                                 "active": 0, "severity": 63, "period": "1-7,00:00-24:00"}]
        users[username] = api.call("user.create", params)["userids"][0]
    return users


def mail_action_definition(host_group_id: str, operator_id: str, media_type_id: str) -> dict:
    return {
        "name": ACTION_NAME, "eventsource": 0, "status": 0,
        "filter": {"evaltype": 0, "conditions": [{"conditiontype": 0, "operator": 0, "value": host_group_id}]},
        "operations": [{"operationtype": 0, "esc_step_from": 1, "esc_step_to": 1,
                        "opmessage_usr": [{"userid": operator_id}],
                        "opmessage": {"default_msg": 1, "mediatypeid": media_type_id}}],
        "recovery_operations": [{"operationtype": 11, "opmessage": {"default_msg": 1}}],
    }


def ensure_action(api, host_group_id: str, operator_id: str, media_type_id: str) -> str:
    definition = mail_action_definition(host_group_id, operator_id, media_type_id)
    existing = single(api, "action.get", "name", ACTION_NAME, ["actionid", "name"])
    if existing:
        api.call("action.update", {"actionid": existing["actionid"], **{k: v for k, v in definition.items() if k != "eventsource"}})
        return existing["actionid"]
    return api.call("action.create", definition)["actionids"][0]


def dashboard_definition(host_group_id: str, item_ids: dict, user_group_ids: list[str], map_id: str | None = None) -> dict:
    group_field = {"type": 2, "name": "groupids.0", "value": host_group_id}
    widgets = [
        {"type": "hostavail", "name": "Tinh trang Agent/SNMP", "x": 0, "y": 0,
         "width": 24, "height": 4, "fields": [group_field]},
        {"type": "problems", "name": "Su co A1 Lab", "x": 24, "y": 0,
         "width": 48, "height": 8, "fields": [group_field]},
    ]
    placements = [("ping", "ICMP Ping", 0, 4), ("loss", "Packet loss", 12, 4),
                  ("rtt", "Response time", 0, 8), ("cpu", "Linux CPU", 12, 8),
                  ("memory", "Linux RAM", 24, 8), ("disk", "Linux disk", 36, 8),
                  ("snmp_in", "SNMP traffic in", 48, 8)]
    for key, label, x, y in placements:
        if key in item_ids:
            widgets.append({"type": "item", "name": label, "x": x, "y": y,
                            "width": 12, "height": 4,
                            "fields": [{"type": 4, "name": "itemid.0", "value": item_ids[key]}]})
    for key, label, x in (("rtt", "ICMP response trend", 0), ("snmp_in", "SNMP traffic trend", 36)):
        if key in item_ids:
            widgets.append({"type": "graph", "name": label, "x": x, "y": 12,
                            "width": 36, "height": 6,
                            "fields": [{"type": 0, "name": "source_type", "value": 1},
                                       {"type": 4, "name": "itemid.0", "value": item_ids[key]},
                                       {"type": 1, "name": "reference", "value": "PINGA" if key == "rtt" else "SNMPA"}]})
    if map_id:
        widgets.append({"type": "map", "name": "A1 Lab logical host map", "x": 0, "y": 18,
                        "width": 72, "height": 8,
                        "fields": [{"type": 8, "name": "sysmapid.0", "value": map_id},
                                   {"type": 1, "name": "reference", "value": "MAPA1"}]})
    return {"name": DASHBOARD_NAME, "private": 0, "display_period": 30,
            "pages": [{"name": "Tong quan", "widgets": widgets}],
            "userGroups": [{"usrgrpid": group_id, "permission": 2} for group_id in user_group_ids]}


def find_item_ids(api, hosts: dict) -> dict:
    candidates = {
        "ping": ("A1-LAB-ENDPOINT", "icmpping"),
        "loss": ("A1-LAB-ENDPOINT", "icmppingloss"),
        "rtt": ("A1-LAB-ENDPOINT", "icmppingsec"),
        "cpu": ("lab-linux-agent", "system.cpu.util"),
        "memory": ("lab-linux-agent", "vm.memory.size[pavailable]"),
        "disk": ("lab-linux-agent", "vfs.fs.size[/,pused]"),
    }
    found = {}
    for label, (host_name, key) in candidates.items():
        rows = api.call("item.get", {"output": ["itemid", "key_", "status", "state"],
                                     "hostids": hosts[host_name], "filter": {"key_": [key]}})
        if rows:
            found[label] = rows[0]["itemid"]
    snmp_items = api.call("item.get", {"output": ["itemid", "key_", "name", "status"],
                                       "hostids": hosts["A1-LAB-SNMP"], "search": {"key_": "net.if.in"}})
    snmp_items = [item for item in snmp_items if str(item.get("status")) == "0"]
    if snmp_items:
        found["snmp_in"] = snmp_items[0]["itemid"]
    return found


def ensure_dashboard(api, host_group_id: str, hosts: dict, user_group_ids: list[str], map_id: str) -> str:
    definition = dashboard_definition(host_group_id, find_item_ids(api, hosts), user_group_ids, map_id)
    existing = single(api, "dashboard.get", "name", DASHBOARD_NAME, ["dashboardid", "name"])
    if existing:
        api.call("dashboard.update", {"dashboardid": existing["dashboardid"], **definition})
        return existing["dashboardid"]
    return api.call("dashboard.create", definition)["dashboardids"][0]


def lab_map_definition(hosts: dict, icons: dict, user_group_ids: list[str]) -> dict:
    layout = [
        ("A1-LAB-ENDPOINT", "Cloud_(48)", 100, 130, "ICMP endpoint"),
        ("lab-linux-agent", "Server_(48)", 390, 130, "Linux Agent"),
        ("A1-LAB-SNMP", "Network_(48)", 245, 320, "SNMP source"),
    ]
    elements = []
    for number, (host_name, icon_name, x, y, label) in enumerate(layout, 1):
        elements.append({"selementid": str(number), "elements": [{"hostid": hosts[host_name]}],
                         "elementtype": 0, "iconid_off": icons[icon_name],
                         "label": label, "x": x, "y": y})
    return {"name": MAP_NAME, "width": 600, "height": 460, "private": 1,
            "selements": elements,
            "userGroups": [{"usrgrpid": group_id, "permission": 2} for group_id in user_group_ids]}


def ensure_map(api, hosts: dict, user_group_ids: list[str]) -> str:
    existing = single(api, "map.get", "name", MAP_NAME, ["sysmapid", "name"])
    if existing:
        return existing["sysmapid"]
    icons = {}
    for name in ("Cloud_(48)", "Server_(48)", "Network_(48)"):
        image = single(api, "image.get", "name", name, ["imageid", "name"])
        if not image:
            raise ZabbixError(f"Missing default Zabbix icon: {name}")
        icons[name] = image["imageid"]
    return api.call("map.create", lab_map_definition(hosts, icons, user_group_ids))["sysmapids"][0]


def provision(api, project_dir: Path) -> dict:
    settings = read_settings(project_dir)
    group_id = ensure_host_group(api)
    hosts = ensure_hosts(api, group_id, settings)
    zones = ensure_zone_groups(api, group_id, hosts)
    ensure_disk_item(api, hosts["lab-linux-agent"])
    ensure_latency_trigger(api, hosts["A1-LAB-ENDPOINT"])
    media_id = ensure_media_type(api)
    operator_group_id = ensure_user_group(api, "A1 Lab Operators", group_id, 3)
    viewer_group_id = ensure_user_group(api, "A1 Lab Viewers", group_id, 2)
    users = ensure_users(api, project_dir, operator_group_id, viewer_group_id, media_id)
    action_id = ensure_action(api, group_id, users["a1-operator"], media_id)
    map_id = ensure_map(api, hosts, [operator_group_id, viewer_group_id])
    dashboard_id = ensure_dashboard(api, group_id, hosts, [operator_group_id, viewer_group_id], map_id)
    return {"group_id": group_id, "hosts": hosts, "media_type_id": media_id,
            "zones": zones, "users": users, "action_id": action_id,
            "map_id": map_id, "dashboard_id": dashboard_id}
