"""Verify the camera's HTTPS WebRTC page and WHIP signaling."""
from pathlib import Path
import configparser,urllib.request,urllib.parse,ssl,base64
root=Path(__file__).resolve().parents[1]
c=configparser.ConfigParser(interpolation=None)
c.read(root/"backups/pre-raptor-20261014/raptor.conf")
auth=base64.b64encode((c["webrtc"]["username"]+":"+c["webrtc"]["password"]).encode()).decode()
headers={"Authorization":"Basic "+auth}
context=ssl._create_unverified_context()
base="https://192.168.1.54:8554"
with urllib.request.urlopen(urllib.request.Request(base+"/webrtc",headers=headers),context=context,timeout=15) as r:
    assert r.status==200
    print("WEBRTC_HTTPS_PAGE_PASS bytes=",len(r.read()))
offer="\r\n".join([
"v=0","o=- 0 0 IN IP4 127.0.0.1","s=-","t=0 0","a=group:BUNDLE 0",
"m=video 9 UDP/TLS/RTP/SAVPF 96","c=IN IP4 0.0.0.0","a=mid:0",
"a=ice-ufrag:k5check","a=ice-pwd:abcdefghijklmnopqrstuvwx",
"a=fingerprint:sha-256 "+":".join(["00"]*32),"a=setup:actpass",
"a=rtcp-mux","a=recvonly","a=rtpmap:96 H264/90000",
"a=fmtp:96 packetization-mode=1;profile-level-id=42001f;level-asymmetry-allowed=1",
"a=rtcp-fb:96 nack",""])
h=dict(headers,**{"Content-Type":"application/sdp"})
req=urllib.request.Request(base+"/whip",data=offer.encode(),headers=h,method="POST")
with urllib.request.urlopen(req,context=context,timeout=15) as r:
    answer=r.read().decode()
    assert r.status==201 and "a=fingerprint:sha-256" in answer and "a=candidate:" in answer
    assert "192.168.1.54" in answer
    location=r.headers.get("Location")
    print("WHIP_SDP_HANDSHAKE_PASS status=",r.status)
if location:
    req=urllib.request.Request(urllib.parse.urljoin(base,location),headers=headers,method="DELETE")
    with urllib.request.urlopen(req,context=context,timeout=15) as r:
        print("WHIP_TEST_SESSION_CLOSED status=",r.status)
