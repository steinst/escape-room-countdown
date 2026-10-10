# Running on a Raspberry Pi 3

Turns an SD card into a TV appliance: it boots straight into the countdown,
fullscreen over HDMI (with HDMI audio), no desktop needed.

## Flash the card

1. Download **Raspberry Pi OS Lite (64-bit)** from
   <https://www.raspberrypi.com/software/operating-systems/> (the `.img.xz`)
   and put it in this folder.
2. Insert the card and find its device (`lsblk`), then in a normal terminal:

   ```bash
   sudo python3 flash_sd.py /dev/sdX
   ```

   This **erases the card**. The script refuses anything that isn't a
   removable disk of about 20–40 GB and makes you retype the device name. It
   asks for your Wi-Fi name/password and a login password for the user
   `escape`; they are written only to the card.

   Close any file manager window showing the card first, or unmount fails.
3. Put the card in the Pi, connect HDMI and a USB keyboard, power on. The
   first boot needs Wi-Fi (2.4 GHz; the Pi 3 can't use 5 GHz) to install
   dependencies, about 5–10 minutes. Use a proper 5 V / 2.5 A supply —
   undervoltage causes failures.

If the install didn't run (no `startx` afterwards), log in on the Pi and run
`sudo bash /usr/local/sbin/escape-setup.sh`; the log is
`/var/log/escape-setup.log`.

## Settings (edit from any computer, on the card's `bootfs` partition)

- `countdown.txt` — first line is the length: `45m`, `90s`, `05:00` …
- `escape-countdown.toml` — stop word and taglines

On the Pi: `echo 45m | sudo tee /boot/firmware/countdown.txt`, then Ctrl+Q
restarts the app with the new value. The keyboard layout is Icelandic.

## Using it

- **Ctrl+Q** quits, but the Pi logs in again and restarts the app.
- For a command line while the app keeps running: **Ctrl+Alt+F2**, log in as
  `escape`; **Ctrl+Alt+F1** returns to the app. To stop the app for the
  session: `sudo systemctl stop getty@tty1`.
- The screen is set to 1280x720 (see `~/.xinitrc` on the Pi) because 1080p is too slow for a Pi 3.
- The program lives in `/opt/escape-countdown` on the Pi. To update it over
  SSH: `scp -o PubkeyAuthentication=no countdown.py escape@<pi-ip>:/opt/escape-countdown/`
