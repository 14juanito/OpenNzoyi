"""Parser tests for the Phase 2 tool wrappers (no binaries required)."""

from tools.implementations.nmap import NmapTool
from tools.implementations.nuclei import NucleiTool
from tools.implementations.netexec import NetexecTool

NMAP_XML = """<?xml version="1.0"?>
<nmaprun>
  <host>
    <address addr="192.168.100.11" addrtype="ipv4"/>
    <ports>
      <port protocol="tcp" portid="22"><state state="open"/>
        <service name="ssh" product="OpenSSH" version="8.9p1"/></port>
      <port protocol="tcp" portid="80"><state state="open"/>
        <service name="http" product="Apache httpd" version="2.4.52"/></port>
      <port protocol="tcp" portid="443"><state state="closed"/>
        <service name="https"/></port>
    </ports>
  </host>
</nmaprun>"""

NUCLEI_JSONL = (
    '{"template-id":"apache-version","info":{"name":"Apache Detect","severity":"info"},"matched-at":"http://192.168.100.11:80"}\n'
    '{"template-id":"CVE-2021-41773","info":{"name":"Path Traversal","severity":"high"},"matched-at":"http://192.168.100.11:80/cgi-bin"}\n'
    "garbage line that is not json\n"
)

NXC_OUT = (
    "SMB  192.168.100.20  445  DC01  [*] Windows Server 2022 (name:DC01) (domain:CORP.LOCAL) (signing:True)\n"
)


def test_nmap_parse_open_ports_only():
    parsed = NmapTool().parse(NMAP_XML)
    assert parsed["open_ports"] == [22, 80]  # 443 closed excluded
    assert parsed["hosts"][0]["address"] == "192.168.100.11"
    assert any(p["service"] == "http" for p in parsed["hosts"][0]["ports"])


def test_nmap_parse_bad_xml_never_raises():
    assert NmapTool().parse("not xml <<")["open_ports"] == []


def test_nuclei_parse_sorts_by_severity_and_skips_garbage():
    parsed = NucleiTool().parse(NUCLEI_JSONL)
    assert parsed["count"] == 2
    assert parsed["findings"][0]["severity"] == "high"  # sorted desc
    assert parsed["findings"][0]["template_id"] == "CVE-2021-41773"


def test_netexec_parse_host_domain():
    parsed = NetexecTool().parse(NXC_OUT)
    assert parsed["hosts"][0]["domain"] == "CORP.LOCAL"
    assert parsed["hosts"][0]["name"] == "DC01"
    assert parsed["hosts"][0]["signing"] == "True"
