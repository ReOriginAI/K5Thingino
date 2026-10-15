"""Check live RTSP media and snapshots without printing credentials."""
from pathlib import Path
import json,subprocess,tarfile,urllib.parse,urllib.request,base64,ssl
root=Path(__file__).resolve().parents[1]
with tarfile.open(root/"backups/pre-raptor-20261014/configs.tar") as tar:
    old=json.load(tar.extractfile("etc/prudynt.json"))
auth=old["rtsp"]
user=auth["username"]; password=auth["password"]
endpoint=old["stream0"]["rtsp_endpoint"]
url="rtsp://"+urllib.parse.quote(user,safe="")+":"+urllib.parse.quote(password,safe="")+"@192.168.1.54:554/"+endpoint
args=["ffprobe","-v","error","-rtsp_transport","tcp","-timeout","10000000","-i",url,"-read_intervals","%+3","-count_frames","-show_entries","stream=index,codec_name,codec_type,width,height,sample_rate,nb_read_frames","-of","json"]
r=subprocess.run(args,text=True,capture_output=True,timeout=30)
if r.returncode:
    raise SystemExit("RTSP_CHECK_FAILED: "+r.stderr.replace(url,"<camera RTSP>").replace(password,"<redacted>"))
data=json.loads(r.stdout)
(root/"docs/logs/raptor-live-stream-20261014.json").write_text(json.dumps(data,indent=2))
assert any(s["codec_type"]=="video" and s["width"]==1920 and int(s.get("nb_read_frames","0"))>0 for s in data["streams"]),data
print("RTSP_MEDIA_PASS",json.dumps(data))
token=base64.b64encode((user+":"+password).encode()).decode()
req=urllib.request.Request("https://192.168.1.54:8443/snap.jpg",headers={"Authorization":"Basic "+token})
with urllib.request.urlopen(req,timeout=15,context=ssl._create_unverified_context()) as response:
    image=response.read()
assert image[:2]==b"\xff\xd8" and image[-2:]==b"\xff\xd9"
print("LIVE_JPEG_PASS bytes=",len(image))
