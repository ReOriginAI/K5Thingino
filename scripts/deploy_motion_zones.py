from pathlib import Path
import shutil,subprocess,json,time,shlex
root=Path(__file__).resolve().parents[1]; repo=root/'thingino-firmware'
archive=root/'archive/motion-zones-20261014'
base=repo/'user/wansview_k5_t21n_ov2735b_rtl8188fu/overlay/var/www'
stage=archive/'ui-stage'; shutil.copytree(root/'archive/raptor-ui-repair-20261014/stage',stage,symlinks=True)
web=stage/'var/www'
for rel in ('motion-zones.html','x/motion-zones.cgi'):
 src=root/'scripts'/Path(rel).name
 text=src.read_text()
 if rel.endswith('.cgi'):
  text=text.replace('[ "$QUERY_STRING" = snapshot ]','[ "${QUERY_STRING%%&*}" = snapshot ]')
 (web/rel).write_text(text)
 if rel.endswith('.cgi'):
  (web/rel).chmod(0o755); subprocess.run(['sh','-n',str(web/rel)],check=True)
manifest=web/'a/plugins/raptor.webui.json'
m=json.loads(manifest.read_text()); m['nav'][1]['items'].insert(1,dict(label='Motion zones',href='/motion-zones.html'))
m['cgi'].append('/x/motion-zones.cgi');manifest.write_text(json.dumps(m,indent=2)+'\n')
subprocess.run(['python3',str(repo/'package/thingino-webui/scripts/assemble_plugins.py'),str(stage)],check=True)
subprocess.run(['python3',str(repo/'package/thingino-webui/scripts/apply_asset_tag.py'),str(int(time.time())),str(web)],check=True)
files=['motion-zones.html','x/motion-zones.cgi','a/plugins/raptor.webui.json','a/plugins.js','index.html','info.html','preview.html']
ssh=['ssh','-S','/tmp/k5-zones-control','root@192.168.1.54']
scp=['scp','-O','-o','ControlPath=/tmp/k5-zones-control']
for i,rel in enumerate(files):
 saved=archive/'ui-before'/rel;saved.parent.mkdir(parents=True,exist_ok=True)
 path='/var/www/'+rel
 exists=subprocess.run(ssh+['test -f '+shlex.quote(path)],capture_output=True).returncode==0
 if exists:subprocess.run(scp+['root@192.168.1.54:'+path,str(saved)],check=True,capture_output=True)
 src=web/rel;dest=base/rel;dest.parent.mkdir(parents=True,exist_ok=True)
 if dest.exists():
  old=archive/'overlay-before'/rel;old.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(dest,old)
 shutil.copy2(src,dest)
 tmp='/tmp/motion-ui-'+str(i)
 subprocess.run(scp+[str(src),'root@192.168.1.54:'+tmp],check=True,capture_output=True)
 mode='755' if rel.endswith('.cgi') else '644'
 subprocess.run(ssh+['cp '+shlex.quote(tmp)+' '+shlex.quote(path+'.new')+' && chmod '+mode+' '+shlex.quote(path+'.new')+' && mv '+shlex.quote(path+'.new')+' '+shlex.quote(path)],check=True)
print('MOTION_ZONES_UI_DEPLOYED')
