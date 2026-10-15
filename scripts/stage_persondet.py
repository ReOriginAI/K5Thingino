from pathlib import Path
import shutil,subprocess,configparser
root=Path(__file__).resolve().parents[1]
out=root/'thingino-firmware/output/stable/wansview_k5_t21n_ov2735b_rtl8188fu-3.10.14-uclibc'
stage=root/'archive/persondet-20261014/stage'
stage.mkdir(exist_ok=False); (stage/'lib').mkdir()
src=out/'per-package/thingino-raptor/target'
for name in ('rvd','rmd'):
 shutil.copy2(src/'usr/bin'/name,stage/name)
 subprocess.run([str(out/'host/bin/mipsel-linux-strip'),'--strip-unneeded',str(stage/name)],check=True)
 subprocess.run([str(out/'host/bin/patchelf'),'--remove-rpath',str(stage/name)],check=True)
libs=['libpersonDet_inf.so','libjzdl.so','libjzdl.m.so','libmxu_core.so','libmxu_imgproc.so','libmxu_merge.so','libmxu_video.so','libstdc++.so.6']
for name in libs:
 f=src/'usr/lib'/name
 if not f.exists():
  candidates=list((out/'per-package/thingino-raptor/host').rglob(name))
  assert candidates,name
  f=candidates[0]
 shutil.copy2(f.resolve(),stage/'lib'/name)
 subprocess.run([str(out/'host/bin/mipsel-linux-strip'),'--strip-unneeded',str(stage/'lib'/name)],check=True)
c=configparser.ConfigParser(); c.read(root/'archive/persondet-20261014/raptor.conf.before')
c['stream1'].update(enabled='true',width='640',height='360',fps='5',bitrate='256000',gop='10')
c['motion']=dict(enabled='true',algorithm='persondet',sensitivity='3',skip_frames='5',det_distance='2',motion_trigger='false',record='false',poll_interval_ms='500',cooldown_sec='10')
with (stage/'raptor.conf').open('w') as f:c.write(f)
(stage/'raptor.conf').chmod(0o600)
print('STAGED_BYTES',sum(f.stat().st_size for f in stage.rglob('*') if f.is_file()))
subprocess.run(['ssh','-S','/tmp/k5-persondet-ssh-control','root@192.168.1.54','mkdir -p /tmp/k5-persondet/lib'],check=True)
subprocess.run(['scp','-O','-r','-o','ControlPath=/tmp/k5-persondet-ssh-control',str(stage)+'/.','root@192.168.1.54:/tmp/k5-persondet/'],check=True)
subprocess.run(['ssh','-S','/tmp/k5-persondet-ssh-control','root@192.168.1.54','LD_LIBRARY_PATH=/tmp/k5-persondet/lib /tmp/k5-persondet/rvd -h'],check=True)
