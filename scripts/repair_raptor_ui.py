"""Restore Raptor preview/navigation from the selected streamer's own package."""
from pathlib import Path
import shutil,json,subprocess,time
root=Path(__file__).resolve().parents[1]
repo=root/"thingino-firmware"
out=repo/"output/stable/wansview_k5_t21n_ov2735b_rtl8188fu-3.10.14-uclibc"
repair=root/"archive/raptor-ui-repair-20261014"
stage=repair/"stage"
if stage.exists(): raise SystemExit("UI staging already exists")
shutil.copytree(out/"target/var/www",stage/"var/www",symlinks=True)
web=stage/"var/www"
for name in ("prudynt", "daynightd"):
    legacy=web/"a/plugins"/(name+".webui.json")
    if legacy.exists(): shutil.move(legacy,repair/(name+".webui.json.previous"))
manifest={
"name":"raptor","label":"Raptor Streaming System","apiVersion":1,
"nav":[
 {"section":"ddInfo","position":"append","items":[{"label":"File: raptor.conf","href":"/info.html?raptor"}]},
 {"section":"ddStreamer","position":"append","items":[
  {"label":"Live preview","href":"/preview.html"},
  {"label":"Raptor configuration","href":"/info.html?raptor"},
  {"label":"Streamer log","href":"/info.html?logread"},
  {"type":"divider"},
  {"label":"Restart Raptor","href":"/x/restart-raptor.cgi","className":"text-danger confirm","trackActive":False}
 ]}
],"scripts":[],"styles":[],"preview":{"scripts":[],"html":None},
"featureFlags":{"raptor":True},"cgi":["/x/restart-raptor.cgi"],"pages":[]}
(web/"a/plugins/raptor.webui.json").write_text(json.dumps(manifest,indent=2)+"\n")
shutil.copy2(repo/"package/thingino-raptor/files/www/preview.html",web/"preview.html")
proxy=repo/"package/thingino-raptor/files/www/x/webrtc-whip.cgi"
text=proxy.read_text()
assert text.count("set -eu")==1
text=text.replace("set -eu","set -eu\nHTTP_COOKIE=${HTTP_COOKIE:-}\nHTTP_X_API_KEY=${HTTP_X_API_KEY:-}\nHTTP_ACCEPT=${HTTP_ACCEPT:-}\nQUERY_STRING=${QUERY_STRING:-}\n\n. /var/www/x/auth.sh\nrequire_auth",1)
(web/"x/webrtc-whip.cgi").write_text(text)
(web/"x/webrtc-whip.cgi").chmod(0o755)
restart=repo/"package/prudynt-t/files/www/x/restart-prudynt.cgi"
text=restart.read_text().replace("Restart prudynt service","Restart Raptor service").replace("service restart prudynt","/etc/init.d/S31raptor restart")
(web/"x/restart-raptor.cgi").write_text(text)
(web/"x/restart-raptor.cgi").chmod(0o755)
subprocess.run(["python3",str(repo/"package/thingino-webui/scripts/assemble_plugins.py"),str(stage)],check=True)
subprocess.run(["python3",str(repo/"package/thingino-webui/scripts/apply_asset_tag.py"),str(int(time.time())),str(web)],check=True)
deliver=["preview.html","index.html","info.html","a/plugins.js","a/plugins/raptor.webui.json","x/webrtc-whip.cgi","x/restart-raptor.cgi"]
overlay=repo/"user/wansview_k5_t21n_ov2735b_rtl8188fu/overlay/var/www"
for relative in deliver:
 p=web/relative
 assert p.exists(),relative
 dest=overlay/relative
 dest.parent.mkdir(parents=True,exist_ok=True)
 shutil.copy2(p,dest)
preview=(web/"preview.html").read_text()
assert "raptor-webrtc-video" in preview and "prudynt" not in preview.lower()
bundle=(web/"a/plugins.js").read_text()
assert '"name": "prudynt"' not in bundle and "File: raptor.conf" in bundle
for p in (web/"x/webrtc-whip.cgi",web/"x/restart-raptor.cgi"):
 subprocess.run(["/bin/sh","-n",str(p)],check=True)
(repair/"files.json").write_text(json.dumps(deliver,indent=2))
print("RAPTOR_UI_QA_PASS",deliver)
