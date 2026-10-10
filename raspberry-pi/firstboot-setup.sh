#!/bin/bash
# Runs once as root via cloud-init on first boot (needs network).
exec > >(tee -a /var/log/escape-setup.log) 2>&1
set -x
APP=/opt/escape-countdown
U=escape

# wait for network
for i in $(seq 1 60); do
  getent hosts deb.debian.org >/dev/null && break
  sleep 5
done

for i in 1 2 3 4 5; do apt-get update && break; sleep 15; done
DEBIAN_FRONTEND=noninteractive apt-get install -y --no-install-recommends \
  xserver-xorg xserver-xorg-input-libinput xserver-xorg-legacy xinit x11-xserver-utils \
  unclutter python3-venv python3-pip libcairo2 fonts-dejavu-core alsa-utils \
  || { echo "apt install failed"; exit 1; }

# keyboard (also covers the X session)
cat > /etc/default/keyboard <<K
XKBMODEL="pc105"
XKBLAYOUT="is"
XKBVARIANT=""
XKBOPTIONS=""
K

# send sound to HDMI (the Pi 3 defaults to the headphone jack)
cat > /etc/asound.conf <<S
pcm.!default {
    type plug
    slave.pcm "plughw:vc4hdmi,0"
}
ctl.!default {
    type hw
    card vc4hdmi
}
S

chown -R $U:$U $APP
sudo -u $U python3 -m venv $APP/venv
sudo -u $U $APP/venv/bin/pip install --no-cache-dir -r $APP/requirements.txt || { echo "pip failed"; exit 1; }

# X session: runs the countdown, restarts it if it exits/crashes (Ctrl+Q ends it for real)
cat > /home/$U/.xinitrc <<'X'
#!/bin/sh
xset s off -dpms
xset s noblank
unclutter -idle 0 &
DUR=$(grep -v '^#' /boot/firmware/countdown.txt 2>/dev/null | head -1 | tr -d '[:space:]')
CFG=/boot/firmware/escape-countdown.toml
[ -f "$CFG" ] || CFG=/opt/escape-countdown/config.toml
cd /opt/escape-countdown
SDL_VIDEODRIVER=x11 exec ./venv/bin/python countdown.py "${DUR:-60m}" --config "$CFG"
X
chown $U:$U /home/$U/.xinitrc
chmod +x /home/$U/.xinitrc

# start X automatically on the tty1 login
cat >> /home/$U/.bash_profile <<'P'
if [ -z "$DISPLAY" ] && [ "$(tty)" = /dev/tty1 ]; then
  exec startx -- -nocursor
fi
P
chown $U:$U /home/$U/.bash_profile

# console autologin on tty1 (enabled last so the app never starts half-installed)
mkdir -p /etc/systemd/system/getty@tty1.service.d
cat > /etc/systemd/system/getty@tty1.service.d/autologin.conf <<A
[Service]
ExecStart=
ExecStart=-/sbin/agetty --autologin $U --noclear %I \$TERM
A
systemctl daemon-reload
systemctl enable ssh
touch $APP/.installed
systemctl restart getty@tty1
