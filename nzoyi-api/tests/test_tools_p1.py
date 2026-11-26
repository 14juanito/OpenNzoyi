"""Parser tests for the P0/P1 catalogue tools (Phase 3, no binaries)."""

from tools.registry import default_registry
from tools.implementations.rustscan import RustscanTool
from tools.implementations.httpx import HttpxTool
from tools.implementations.subfinder import SubfinderTool
from tools.implementations.ffuf import FfufTool
from tools.implementations.sqlmap import SqlmapTool
from tools.implementations.nikto import NiktoTool
from tools.implementations.impacket import ImpacketTool
from tools.implementations.bloodhound import BloodHoundTool
from tools.implementations.linux_exploit_suggester import LinuxExploitSuggesterTool
from tools.implementations.linpeas import LinpeasTool


def test_registry_lists_full_catalogue():
    reg = default_registry()
    for name in ("nmap", "rustscan", "httpx", "subfinder", "nuclei", "ffuf",
                 "sqlmap", "nikto", "netexec", "impacket", "bloodhound",
                 "sharphound", "linpeas", "linux-exploit-suggester", "chisel"):
        assert reg.get(name) is not None, name
    # phase routing
    assert {t.name for t in reg.for_phase("recon")} >= {"nmap", "rustscan", "httpx"}
    assert {t.name for t in reg.for_phase("vuln")} >= {"nuclei", "ffuf", "sqlmap"}


def test_rustscan_parse():
    out = "Open 192.168.100.11:22\nOpen 192.168.100.11:80\nOpen 192.168.100.11:80\n"
    assert RustscanTool().parse(out)["open_ports"] == [22, 80]


def test_httpx_parse():
    out = '{"url":"http://x","status_code":200,"title":"Home","tech":["nginx"]}\nbad\n'
    p = HttpxTool().parse(out)
    assert p["count"] == 1 and p["urls"][0]["status_code"] == 200


def test_subfinder_parse_dedups():
    out = "a.example.com\nb.example.com\na.example.com\n"
    assert SubfinderTool().parse(out)["subdomains"] == ["a.example.com", "b.example.com"]


def test_ffuf_parse():
    out = ".git/config             [Status: 200, Size: 92, Words: 3, Lines: 4]\n"
    p = FfufTool().parse(out)
    assert p["hits"][0]["path"] == ".git/config" and p["hits"][0]["status"] == 200


def test_sqlmap_parse_detects_injection():
    out = ("sqlmap identified the following injection point\n"
           "Parameter: id (GET)\n    Type: boolean-based blind\n")
    p = SqlmapTool().parse(out)
    assert p["vulnerable"] is True
    assert p["injection_points"][0]["parameter"] == "id"


def test_nikto_parse():
    out = "+ Server: Apache/2.4.52\n+ OSVDB-3233: /icons/README CVE-1999-0001\n- skip\n"
    p = NiktoTool().parse(out)
    assert p["count"] == 2
    assert "OSVDB-3233" in p["items"][1]["refs"]


def test_impacket_destructive_flag():
    assert ImpacketTool("GetADUsers").requires_interception is False
    assert ImpacketTool("secretsdump").requires_interception is True


def test_bloodhound_parse_counts():
    out = "INFO: Found 42 users\nINFO: Found 7 computers\n"
    assert BloodHoundTool().parse(out)["collected"] == {"users": 42, "computers": 7}


def test_les_parse_sorts_probable_first():
    out = ("[+] [CVE-2016-5195] dirtycow  Exposure: less probable\n"
           "[+] [CVE-2021-4034] pwnkit  Exposure: probable\n")
    p = LinuxExploitSuggesterTool().parse(out)
    assert p["suggestions"][0]["cve"] == "CVE-2021-4034"  # probable first


def test_linpeas_parse_pe_vectors():
    out = "Checking sudo\n95% | /etc/passwd writable\nCVE-2021-4034 present\n"
    p = LinpeasTool().parse(out)
    assert p["count"] == 1 and "CVE-2021-4034" in p["cves"]
