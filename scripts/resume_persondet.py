from pathlib import Path
import os,subprocess
root=Path(__file__).resolve().parents[1]; checkout=root/'thingino-firmware'
out=checkout/'output/stable/wansview_k5_t21n_ov2735b_rtl8188fu-3.10.14-uclibc'
f=checkout/'user/wansview_k5_t21n_ov2735b_rtl8188fu/local.fragment'
f.write_text(f.read_text().replace('# BR2_PACKAGE_THINGINO_RAPTOR_IVS_JZDL is not set','BR2_PACKAGE_THINGINO_RAPTOR_IVS_JZDL=y'))
env=dict(os.environ,CAMERA='wansview_k5_t21n_ov2735b_rtl8188fu',IP='192.168.1.54',WORKFLOW='1',THINGINO_OUTPUT_DIR=str(out))
localtools=root/'tools/local-toolchain/usr'
env['PATH']=str(localtools/'bin')+os.pathsep+env.get('PATH','')
env['LD_LIBRARY_PATH']=str(localtools/'lib/x86_64-linux-gnu')
with (root/'docs/logs/persondet-build-resume-20261014.log').open('w') as log:
 for goal in ('force-config','br-ingenic-lib-reconfigure','br-thingino-raptor-reconfigure'):
  print('GOAL',goal,flush=True)
  subprocess.run(['make','--no-print-directory',goal],cwd=checkout,env=env,stdout=log,stderr=subprocess.STDOUT,check=True)
print('PERSONDET_CANDIDATE_BUILT',flush=True)
