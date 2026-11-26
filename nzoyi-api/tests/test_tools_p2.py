"""P2 tool tests (post/lateral/evasion) — parsers + interception defaults."""

from tools.registry import default_registry
from tools.implementations.certipy import CertipyTool
from tools.implementations.rubeus import RubeusTool
from tools.implementations.mimikatz import MimikatzTool
from tools.implementations.winpeas import WinpeasTool
from tools.implementations.sdn_toolkit import SdnToolkitTool
from tools.implementations.scapy_evasion import ScapyEvasionTool
from tools.implementations.evil_winrm import EvilWinrmTool


def test_registry_has_p2_tools():
    reg = default_registry()
    for name in ("certipy", "evil-winrm", "rubeus", "mimikatz", "winpeas",
                 "sdn-toolkit", "scapy_evasion"):
        assert reg.get(name) is not None, name
    assert {t.name for t in reg.for_phase("post")} >= {"mimikatz", "rubeus", "winpeas", "certipy"}
    assert {t.name for t in reg.for_phase("evasion")} >= {"sdn-toolkit", "scapy_evasion"}


def test_destructive_tools_require_interception():
    assert MimikatzTool().requires_interception is True
    assert RubeusTool().requires_interception is True
    assert EvilWinrmTool().requires_interception is True
    assert ScapyEvasionTool().requires_interception is True
    # certipy: enumeration safe, exploitation gated
    assert CertipyTool("find").requires_interception is False
    assert CertipyTool("req").requires_interception is True
    # sdn: read safe, modify gated
    assert SdnToolkitTool("dump-flows").requires_interception is False
    assert SdnToolkitTool("add-flow").requires_interception is True


def test_certipy_parse_esc():
    out = "Certificate Templates\n  [!] Vulnerabilities: ESC1, ESC8\n"
    assert CertipyTool().parse(out)["vulnerable_templates"] == ["ESC1", "ESC8"]


def test_mimikatz_parse_counts_creds():
    out = "Username : admin\nPassword : S3cret!\nNTLM     : (null)\n"
    assert MimikatzTool().parse(out)["credentials_found"] == 1  # (null) excluded


def test_rubeus_parse_tickets():
    out = "$krb5tgs$23$*svc*...\n$krb5tgs$23$*sql*...\n"
    assert RubeusTool().parse(out)["tickets"] == 2


def test_winpeas_parse_vectors():
    out = "  [!] AlwaysInstallElevated enabled\n  normal line\n  [!] Unquoted path svc\n"
    p = WinpeasTool().parse(out)
    assert p["count"] == 2


def test_sdn_parse_drop_flows():
    out = ("cookie=0x0, table=0, actions=drop\n"
           "cookie=0x0, table=0, actions=output:2\n")
    p = SdnToolkitTool().parse(out)
    assert p["drop_flows"] == 1 and p["flow_count"] == 2
