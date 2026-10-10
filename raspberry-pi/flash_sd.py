#!/usr/bin/env python3
"""Flash Raspberry Pi OS Lite to an SD card and preconfigure it to run
escape-countdown fullscreen on boot.

Download the image first (see README.md in this folder), then run in a
normal terminal:   sudo python3 flash_sd.py /dev/sdX [image.img.xz]
If no image is given, the single *.img.xz next to this script is used.

Prompts for the Wi-Fi name/password and a login password. The Pi needs Wi-Fi
once, on first boot, to install dependencies (~5-10 min); after that
it boots straight into the countdown and needs no network.
"""
import getpass
import json
import os
import shutil
import subprocess
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
APP = HERE.parent
USER = "escape"
HOSTNAME = "escape-pi"
DEFAULT_DURATION = "60m"
BOOT = Path("/mnt/pi-boot")
ROOT = Path("/mnt/pi-root")


def run(*cmd, **kw):
    return subprocess.run(cmd, check=True, **kw)


def part(dev, n):
    return f"{dev}p{n}" if dev[-1].isdigit() else f"{dev}{n}"


def check_device(dev):
    name = os.path.basename(dev)
    sysdir = Path("/sys/block") / name
    if not sysdir.exists():
        sys.exit(f"{dev} is not a whole-disk block device")
    removable = (sysdir / "removable").read_text().strip() == "1"
    size_gb = int((sysdir / "size").read_text()) * 512 / 1e9
    mounts = Path("/proc/mounts").read_text()
    if not removable or not (20 < size_gb < 40):
        sys.exit(f"Refusing: {dev} removable={removable} size={size_gb:.1f}GB (expected a ~32GB removable card)")
    if any(l.split()[1] == "/" and l.startswith(dev) for l in mounts.splitlines()):
        sys.exit("Refusing: device holds the root filesystem")
    print(run("lsblk", "-o", "NAME,SIZE,MODEL,TRAN,LABEL,MOUNTPOINTS", dev, capture_output=True, text=True).stdout)
    print(f"ALL DATA ON {dev} ({size_gb:.1f} GB) WILL BE ERASED.")
    if input(f"Type the device name ({dev}) to continue: ").strip() != dev:
        sys.exit("Aborted.")


def user_data(pw_hash):
    setup = (HERE / "firstboot-setup.sh").read_text()
    indented = "".join("      " + l if l.strip() else "\n" for l in setup.splitlines(True))
    return f"""#cloud-config
hostname: {HOSTNAME}
manage_etc_hosts: true
timezone: Atlantic/Reykjavik
keyboard:
  layout: is
ssh_pwauth: true
users:
  - name: {USER}
    groups: [sudo, audio, video, input, render, netdev]
    shell: /bin/bash
    lock_passwd: false
    passwd: {pw_hash}
write_files:
  - path: /usr/local/sbin/escape-setup.sh
    permissions: "0755"
    content: |
{indented}
runcmd:
  - [bash, /usr/local/sbin/escape-setup.sh]
"""


def network_config(ssid, psk):
    return f"""network:
  version: 2
  wifis:
    wlan0:
      dhcp4: true
      optional: true
      regulatory-domain: IS
      access-points:
        {json.dumps(ssid)}:
          password: {json.dumps(psk)}
"""


def main():
    if os.geteuid() != 0:
        sys.exit("Run with sudo.")
    if len(sys.argv) not in (2, 3):
        sys.exit("usage: sudo python3 flash_sd.py /dev/sdX [image.img.xz]")
    dev = sys.argv[1]
    if len(sys.argv) == 3:
        image = Path(sys.argv[2])
    else:
        found = sorted(HERE.glob("*.img.xz"))
        if len(found) != 1:
            sys.exit(f"Put exactly one *.img.xz in {HERE} or pass the image path (found {len(found)})")
        image = found[0]
    for p in (image, APP / "countdown.py"):
        if not p.exists():
            sys.exit(f"missing {p}")
    check_device(dev)

    ssid = input("Wi-Fi name (SSID): ").strip()
    psk = getpass.getpass("Wi-Fi password: ")
    while True:
        pw = getpass.getpass(f"Password for Pi login '{USER}' (for SSH/console): ")
        if len(pw) >= 6 and pw == getpass.getpass("Repeat: "):
            break
        print("Passwords must match and be at least 6 characters.")
    pw_hash = run("openssl", "passwd", "-6", "-stdin", input=pw, capture_output=True, text=True).stdout.strip()

    mounted = [l.split()[0] for l in Path("/proc/mounts").read_text().splitlines() if l.startswith(dev)]
    if mounted:
        run("umount", *mounted)

    print("Writing image (a few minutes)...")
    subprocess.run(f"xz -dc '{image}' | dd of={dev} bs=4M conv=fsync status=progress", shell=True, check=True)
    run("sync")
    run("partprobe", dev)
    run("udevadm", "settle")
    time.sleep(2)

    for d, n in ((BOOT, 1), (ROOT, 2)):
        d.mkdir(parents=True, exist_ok=True)
        run("mount", part(dev, n), str(d))
    try:
        (BOOT / "user-data").write_text(user_data(pw_hash))
        (BOOT / "meta-data").write_text("instance_id: escape-pi-1\n")
        nc = BOOT / "network-config"
        nc.write_text(network_config(ssid, psk))
        nc.chmod(0o600)
        (BOOT / "countdown.txt").write_text(
            f"{DEFAULT_DURATION}\n# Edit the first line: countdown length, e.g. 45m, 60m, 90:00 or 3600\n"
        )
        shutil.copy(APP / "config.toml", BOOT / "escape-countdown.toml")

        dest = ROOT / "opt" / "escape-countdown"
        shutil.copytree(
            APP, dest, ignore=shutil.ignore_patterns("venv", ".git", "__pycache__", "*.pyc", "raspberry-pi")
        )
        print("Installed app to", dest)
    finally:
        run("sync")
        for d in (BOOT, ROOT):
            run("umount", str(d))
    print("\nDone. Remove the card, put it in the Pi 3, connect HDMI + keyboard, power on.")
    print("First boot installs software over Wi-Fi (~5-10 min, console shows progress), then the countdown starts.")


if __name__ == "__main__":
    main()
