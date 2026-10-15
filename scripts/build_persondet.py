"""Build a RAM-testable K5 PersonDet candidate, preserving the installed baseline."""
from pathlib import Path
import os, shutil, subprocess
root=Path(__file__).resolve().parents[1]
checkout=root/'thingino-firmware'
out=checkout/'output/stable/wansview_k5_t21n_ov2735b_rtl8188fu-3.10.14-uclibc'
archive=root/'archive/persondet-20261014'
archive.mkdir(exist_ok=False)
fragment=checkout/'user/wansview_k5_t21n_ov2735b_rtl8188fu/local.fragment'
shutil.copy2(fragment,archive/'local.fragment.before')
shutil.copy2(out/'.config',archive/'config.before')
shutil.copytree(out/'images',archive/'images.before',symlinks=True)
fragment.write_text(fragment.read_text()+"""BR2_PACKAGE_THINGINO_RAPTOR_IVS_DETECT=y
# BR2_PACKAGE_THINGINO_RAPTOR_IVS_JZDL is not set
# BR2_PACKAGE_THINGINO_RAPTOR_IVS_YOLOV5 is not set
BR2_PACKAGE_THINGINO_RAPTOR_IVS_PERSONDET=y
""")
env=dict(os.environ,CAMERA='wansview_k5_t21n_ov2735b_rtl8188fu',IP='192.168.1.54',WORKFLOW='1',THINGINO_OUTPUT_DIR=str(out))
localtools=root/'tools/local-toolchain/usr'
env['PATH']=str(localtools/'bin')+os.pathsep+env.get('PATH','')
env['LD_LIBRARY_PATH']=str(localtools/'lib/x86_64-linux-gnu')
with (root/'docs/logs/persondet-build-20261014.log').open('w') as log:
 def make(goal):
  print('GOAL',goal,flush=True)
  subprocess.run(['make','--no-print-directory',goal],cwd=checkout,env=env,stdout=log,stderr=subprocess.STDOUT,check=True)
 make('force-config')
 for symbol in ('BR2_PACKAGE_THINGINO_RAPTOR_IVS_PERSONDET=y','BR2_PACKAGE_INGENIC_LIB_PERSONDET=y'):
  assert symbol in (out/'.config').read_text(),symbol
 for pattern in ('thingino-raptor-hal-*','thingino-raptor-*'):
  for build in (out/'build').glob(pattern):
   for obj in build.rglob('*.o'):
    dest=archive/'objects.before'/obj.relative_to(out/'build')
    dest.parent.mkdir(parents=True,exist_ok=True)
    shutil.move(str(obj),str(dest))
 for goal in ('br-ingenic-lib-reconfigure','br-thingino-raptor-hal-reconfigure','br-thingino-raptor-reconfigure'):
  make(goal)
print('PERSONDET_CANDIDATE_BUILT',flush=True)
