"""Migrate this camera's private streamer settings without logging credentials."""
from pathlib import Path
import configparser,json,tarfile,os
root=Path(__file__).resolve().parents[1]
out=root/"thingino-firmware/output/stable/wansview_k5_t21n_ov2735b_rtl8188fu-3.10.14-uclibc"
with tarfile.open(root/"backups/pre-raptor-20261014/configs.tar") as tar:
    old=json.load(tar.extractfile("etc/prudynt.json"))
    old_thingino=json.load(tar.extractfile("etc/thingino.json"))
conf=configparser.ConfigParser(interpolation=None,strict=False)
conf.read(out/"target/etc/raptor.conf")
def update(section,values):
    if not conf.has_section(section): conf.add_section(section)
    for key,val in values.items():
        if isinstance(val,bool): val="true" if val else "false"
        val=str(val)
        if "\n" in val or "\r" in val: raise ValueError("Invalid multi-line configuration")
        conf.set(section,key,val)
s=old["sensor"]
update("sensor",dict(name=s["model"],fps=s["fps"],i2c_addr=hex(s["i2c_address"]),i2c_adapter=s["i2c_bus"],rst_gpio=s["gpio_reset"]))
for name in ("stream0","stream1"):
    s=old[name]
    update(name,dict(enabled=s["enabled"],width=s["width"],height=s["height"],fps=s["fps"],codec=s["format"].lower(),profile=s["profile"],bitrate=s["bitrate"]*1000,gop=s["gop"],rc_mode=s["mode"].lower(),jpeg=old["stream2" if name=="stream0" else "stream3"]["enabled"]))
s=old["image"]
update("image",{k:int(s[k]) if isinstance(s[k],bool) else s[k] for k in ("brightness","contrast","saturation","sharpness","hue","max_again","max_dgain","hflip","vflip")})
update("image",dict(sinter=s["sinter_strength"],temper=s["temper_strength"],ae_comp=s["ae_compensation"]))
s=old["audio"]
update("audio",dict(enabled=s["mic_enabled"],codec=s["mic_format"].lower(),sample_rate=16000,input="dmic" if s["mic_is_digital"] else "amic",volume=s["mic_vol"],gain=s["mic_gain"],ao_enabled=s["spk_enabled"],ao_volume=s["spk_vol"],ao_gain=s["spk_gain"],ns_enabled=s["mic_noise_suppression"]>0,ns_level=s["mic_noise_suppression"],hpf_enabled=s["mic_high_pass_filter"],agc_enabled=s["mic_agc_enabled"]))
s=old["rtsp"]
update("rtsp",dict(port=s["port"],endpoint_main=old["stream0"]["rtsp_endpoint"],endpoint_sub=old["stream1"]["rtsp_endpoint"],session_name="Thingino Raptor"))
if s["auth_required"]:
    for section in ("rtsp","http"):
        update(section,dict(username=s["username"],password=s["password"]))
update("ring",dict(main_data_mb=1,main_slots=16,sub_slots=16))
update("ircut",dict(mode=old_thingino["daynight"].get("force_mode","day") if not old_thingino["daynight"].get("enabled",True) else "auto"))
dest=root/"backups/pre-raptor-20261014/raptor.conf"
with dest.open("w") as f: conf.write(f)
os.chmod(dest,0o600)
print("RAPTOR_CONFIG_MIGRATED: sensor, streams, image, audio, endpoints and access credentials")
