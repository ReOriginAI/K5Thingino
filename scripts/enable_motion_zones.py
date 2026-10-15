from pathlib import Path
import configparser,subprocess
root=Path(__file__).resolve().parents[1]; saved=root/'archive/motion-zones-20261014'
before=saved/'raptor.conf.before'; before.chmod(0o600)
c=configparser.ConfigParser(); c.read(before)
c['stream1'].update(enabled='true',width='640',height='360',fps='5',bitrate='256000',gop='10')
c['motion']=dict(enabled='true',algorithm='move',sensitivity='2',grid='4x4',skip_frames='1',poll_interval_ms='250',cooldown_sec='10',record='false',gpio_pin='-1')
p=saved/'raptor.conf.zones'
with p.open('w') as f:c.write(f)
p.chmod(0o600)
subprocess.run(['scp','-O','-o','ControlPath=/tmp/k5-zones-control',str(p),'root@192.168.1.54:/tmp/raptor-motion-zones.conf'],check=True)
subprocess.run(['ssh','-S','/tmp/k5-zones-control','root@192.168.1.54','cp -p /etc/raptor.conf /etc/raptor.conf.pre-zones-20261014 && cp /tmp/raptor-motion-zones.conf /etc/raptor.conf && chmod 600 /etc/raptor.conf && /etc/init.d/S31raptor restart'],check=True)
