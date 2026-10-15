"""Back up and atomically install only the prepared web UI files."""
from pathlib import Path
import subprocess,json,shlex
root=Path(__file__).resolve().parents[1]
repair=root/"archive/raptor-ui-repair-20261014"
files=json.loads((repair/"files.json").read_text())
ssh=["ssh","-S","/tmp/k5-ui-ssh-control","-o","BatchMode=yes","root@192.168.1.54"]
scp=["scp","-O","-o","ControlPath=/tmp/k5-ui-ssh-control","-o","BatchMode=yes"]
def remote(command):
    return subprocess.run(ssh+[command],capture_output=True,text=True,check=True,timeout=20)
for relative in files+["a/plugins/prudynt.webui.json","a/plugins/daynightd.webui.json"]:
    path="/var/www/"+relative
    r=subprocess.run(ssh+["test -f "+shlex.quote(path)],capture_output=True,timeout=10)
    if r.returncode==0:
        saved=repair/"previous"/relative
        if saved.exists():
            continue
        saved.parent.mkdir(parents=True,exist_ok=True)
        subprocess.run(scp+["root@192.168.1.54:"+path,str(saved)],check=True,capture_output=True,timeout=20)
for name in ("prudynt","daynightd"):
    path="/var/www/a/plugins/"+name+".webui.json"
    remote("if [ -f "+shlex.quote(path)+" ]; then mv "+shlex.quote(path)+" "+shlex.quote(path+".disabled-20261014")+"; fi")
for index,relative in enumerate(files):
    source=repair/"stage/var/www"/relative
    tmp="/tmp/k5-raptor-ui-"+str(index)
    path="/var/www/"+relative
    subprocess.run(scp+[str(source),"root@192.168.1.54:"+tmp],check=True,capture_output=True,timeout=20)
    mode="755" if relative.endswith(".cgi") else "644"
    remote("mkdir -p "+shlex.quote(str(Path(path).parent))+" && cp "+shlex.quote(tmp)+" "+shlex.quote(path+".new")+" && chmod "+mode+" "+shlex.quote(path+".new")+" && mv "+shlex.quote(path+".new")+" "+shlex.quote(path))
remote("sync")
print("RAPTOR_WEB_UI_FILES_INSTALLED: native preview, Raptor navigation and authenticated endpoints")
