"""Check the repaired menu, authenticated config view and browser WHIP proxy."""
import urllib.request,urllib.error,urllib.parse,ssl,http.cookiejar,json,base64
base="https://192.168.1.54"
context=ssl._create_unverified_context()
offer="\r\n".join([
"v=0","o=- 0 0 IN IP4 127.0.0.1","s=-","t=0 0","a=group:BUNDLE 0",
"m=video 9 UDP/TLS/RTP/SAVPF 96","c=IN IP4 0.0.0.0","a=mid:0",
"a=ice-ufrag:k5check","a=ice-pwd:abcdefghijklmnopqrstuvwx",
"a=fingerprint:sha-256 "+":".join(["00"]*32),"a=setup:actpass",
"a=rtcp-mux","a=recvonly","a=rtpmap:96 H264/90000",
"a=fmtp:96 packetization-mode=1;profile-level-id=42001f;level-asymmetry-allowed=1",""])
endpoint=base+"/x/webrtc-whip.cgi?stream=0"
req=urllib.request.Request(endpoint,data=offer.encode(),headers={"Content-Type":"application/sdp"})
try:
    urllib.request.urlopen(req,context=context,timeout=15)
    raise AssertionError("Unauthenticated proxy request was accepted")
except urllib.error.HTTPError as e:
    assert e.code==401,e.code
print("UI_PROXY_AUTH_REQUIRED_PASS")
opener=urllib.request.build_opener(urllib.request.HTTPCookieProcessor(http.cookiejar.CookieJar()),urllib.request.HTTPSHandler(context=context))
data=json.dumps({"username":"root","password":"pass"},separators=(",",":")).encode()
req=urllib.request.Request(base+"/x/login.cgi",data=data,headers={"Content-Type":"application/json"})
with opener.open(req,timeout=15) as r: assert json.load(r)["success"]
print("UI_LOGIN_PASS")
with opener.open(base+"/a/plugins.js",timeout=15) as r: bundle=r.read().decode()
assert "File: raptor.conf" in bundle and "prudynt.json" not in bundle
with opener.open(base+"/preview.html",timeout=15) as r: html=r.read().decode()
assert "raptor-webrtc-video" in html and "prudynt" not in html.lower()
print("RAPTOR_MENU_AND_NATIVE_PREVIEW_PASS")
with opener.open(base+"/x/info.cgi?raptor",timeout=15) as r:
    config=json.load(r)
assert config["selected"]=="raptor"
assert "[sensor]" in base64.b64decode(config["commands"][0]["output_base64"]).decode()
print("RAPTOR_CONFIG_VIEW_PASS")
req=urllib.request.Request(endpoint,data=offer.encode(),headers={"Content-Type":"application/sdp"})
with opener.open(req,timeout=20) as r:
    answer=r.read().decode()
    assert r.status==201 and "a=candidate:" in answer
    location=r.headers["Location"]
print("BROWSER_WHIP_PROXY_PASS")
req=urllib.request.Request(base+"/x/webrtc-whip.cgi?session="+urllib.parse.quote(location,safe=""),method="DELETE")
with opener.open(req,timeout=15) as r: assert r.status in (200,204)
print("BROWSER_TEST_SESSION_CLOSED")
