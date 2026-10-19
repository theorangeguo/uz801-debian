#!/usr/bin/env python3
"""Persist a successfully RAM-tested firmware profile, preserving rollback files.

This copies ordinary rootfs files over ADB; it does not write NV or partitions,
dial data, enable data roaming or send SMS. Per-device records stay private.
"""

import argparse
import base64
import hashlib
import json
import re
import subprocess
import time
from pathlib import Path
from firmware_profile import validate_profile


def finish_install(args, profile, trial, report, shell, before_nv):
    remote = trial['remote_tmpfs']
    proc = trial['remoteproc']
    if shell('cat ' + proc + '/state') != 'offline':
        raise RuntimeError('Finish/resume requires the identified modem to be stopped')
    for name, info in profile['files'].items():
        if shell('sha256sum ' + remote + '/' + name).split()[0] != info['sha256']:
            raise RuntimeError('Staged firmware changed')
        destination = '/usr/lib/firmware/' + name
        shell('install -m 0644 ' + remote + '/' + name + ' ' + destination)
        if shell('sha256sum ' + destination).split()[0] != info['sha256']:
            raise RuntimeError('Installed firmware hash mismatch; inspect verified rollback files')
    # Legacy adbd rejects long inline commands. Transfer profile as a file.
    staged_profile = remote + '/installed-profile.json'
    result = subprocess.run([args.adb, '-s', args.serial, 'push', str(args.profile), staged_profile],
                            capture_output=True, timeout=30)
    if result.returncode:
        raise RuntimeError('Profile metadata transfer failed')
    if shell('sha256sum ' + staged_profile).split()[0] != hashlib.sha256(args.profile.read_bytes()).hexdigest():
        raise RuntimeError('Profile metadata hash mismatch')
    shell('install -d /usr/share/uz801 && install -m 0644 ' + staged_profile + ' /usr/share/uz801/modem-firmware-profile.json && sync')
    shell('umount ' + remote)
    shell('systemctl restart rmtfs.service')
    shell("timeout 15 sh -c 'echo start > " + proc + "/state'")
    shell('systemctl start ModemManager.service')
    shell('systemctl restart --no-block uz801-select-sim.service')
    report['physical_nv_unchanged'] = before_nv == shell('sha256sum /dev/disk/by-partlabel/modemst1 /dev/disk/by-partlabel/modemst2 /dev/disk/by-partlabel/fsg /dev/disk/by-partlabel/fsc')
    report['status'] = 'installed-and-hash-verified; restart-and-cold-boot-validation-pending'
    (args.backup_dir / 'deployment.json').write_text(json.dumps(report, indent=2) + '\n', encoding='utf-8')
    print(report['status'], flush=True)
    if not report['physical_nv_unchanged']:
        raise RuntimeError('Physical NV changed unexpectedly')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--adb', default='adb')
    parser.add_argument('--serial', required=True)
    parser.add_argument('--expected-cid', required=True)
    parser.add_argument('--expected-imei', required=True)
    parser.add_argument('--profile', type=Path, required=True)
    parser.add_argument('--source', type=Path, required=True)
    parser.add_argument('--trial', type=Path, required=True)
    parser.add_argument('--backup-dir', type=Path, required=True)
    parser.add_argument('--resume-install', action='store_true',
                        help='Resume an interrupted installation from its verified backup record, on the same boot')
    args = parser.parse_args()
    profile = validate_profile(args.profile, args.source)
    trial = json.loads(args.trial.read_text(encoding='utf-8'))
    if trial.get('status') != 'registered-with-ram-firmware; persistence-and-sms-pending' or not trial.get('physical_nv_unchanged'):
        raise RuntimeError('A successful registration trial with unchanged physical NV is required')
    if trial['cid'] != args.expected_cid or trial['imei'] != args.expected_imei or trial['files'] != profile['files']:
        raise RuntimeError('Trial identity or firmware files do not match')
    mounted = ['/usr/lib/firmware/' + name for name in profile['files']]
    if set(mounted) != set(trial['mounted']):
        raise RuntimeError('Trial contains an unexpected mount set')
    remote = trial['remote_tmpfs']
    if not re.fullmatch(r'/run/fw-trial-[a-f0-9]+-\d+', remote):
        raise RuntimeError('Unexpected trial tmpfs')
    def shell(command, timeout=35):
        wrapped = command + '; result=$?; printf "\\n__FW_DEPLOY_RC__=%s\\n" "$result"'
        result = subprocess.run([args.adb, '-s', args.serial, 'shell', wrapped], capture_output=True, timeout=timeout)
        text = result.stdout.decode('utf-8', errors='replace').replace('\r', '')
        marker = re.search(r'\n__FW_DEPLOY_RC__=(\d+)\s*$', text)
        if result.returncode or not marker or marker.group(1) != '0':
            raise RuntimeError(command + '\n' + text + result.stderr.decode('utf-8', errors='replace'))
        return text[:marker.start()].strip()
    def identity():
        if shell('cat /sys/block/mmcblk0/device/cid') != args.expected_cid:
            raise RuntimeError('Wrong physical device')
    identity()
    if not args.resume_install and args.expected_imei not in shell('mmcli -m any --output-keyvalue'):
        raise RuntimeError('Expected modem IMEI missing')
    backend = shell('systemctl show rmtfs.service -p ActiveState -p ExecStart')
    if 'ActiveState=active' not in backend or ' -r ' not in backend or ' -P ' not in backend:
        raise RuntimeError('Read-only physical-partition rmtfs is required')
    boot = shell('cat /proc/sys/kernel/random/boot_id')
    proc = trial['remoteproc']
    if not re.fullmatch(r'/sys/class/remoteproc/remoteproc\d+', proc):
        raise RuntimeError('Invalid remoteproc')
    if 'DRIVER=qcom-q6v5-mss' not in shell('cat ' + proc + '/device/uevent'):
        raise RuntimeError('Remoteproc is not the modem')
    if args.resume_install:
        report = json.loads((args.backup_dir / 'deployment.json').read_text(encoding='utf-8'))
        if (report['cid'] != args.expected_cid or report['imei'] != args.expected_imei
                or report['profile'] != profile['id'] or report['boot_id'] != boot
                or not report['status'].startswith('installing;')):
            raise RuntimeError('Resume record does not match the interrupted installation')
        if set(report['files']) != set(profile['files']):
            raise RuntimeError('Incomplete rollback record')
        for name, info in report['files'].items():
            if hashlib.sha256((args.backup_dir / name).read_bytes()).hexdigest() != info['original_sha256']:
                raise RuntimeError('Rollback backup hash mismatch')
        audit = json.loads(Path(trial['source_audit']).read_text(encoding='utf-8'))
        if audit['cid'] != args.expected_cid:
            raise RuntimeError('NV audit belongs to another device')
        for name, info in audit['current_physical'].items():
            if shell('sha256sum /dev/disk/by-partlabel/' + name).split()[0] != info['sha256']:
                raise RuntimeError('Physical NV differs from the pre-trial audit')
        before_nv = shell('sha256sum /dev/disk/by-partlabel/modemst1 /dev/disk/by-partlabel/modemst2 /dev/disk/by-partlabel/fsg /dev/disk/by-partlabel/fsc')
        finish_install(args, profile, trial, report, shell, before_nv)
        return
    args.backup_dir.mkdir(parents=True, exist_ok=False)
    report = {'status': 'backing-up', 'profile': profile['id'], 'cid': args.expected_cid,
              'imei': args.expected_imei, 'boot_id': boot, 'files': {}, 'physical_nv_writes': False}
    def save():
        (args.backup_dir / 'deployment.json').write_text(json.dumps(report, indent=2) + '\n', encoding='utf-8')
    def stop_modem():
        for attempt in range(3):
            state = shell('cat ' + proc + '/state')
            if state == 'offline':
                return
            if state != 'running':
                raise RuntimeError('Unexpected modem state: ' + state)
            shell("timeout 15 sh -c 'echo stop > " + proc + "/state'")
            for poll in range(20):
                time.sleep(0.25)
                if shell('cat ' + proc + '/state') == 'offline':
                    return
        raise RuntimeError('Modem did not stop')
    before_nv = shell('sha256sum /dev/disk/by-partlabel/modemst1 /dev/disk/by-partlabel/modemst2 /dev/disk/by-partlabel/fsg /dev/disk/by-partlabel/fsc')
    originals = {}
    for line in (args.trial.parent / 'original-firmware-sha256.txt').read_text().splitlines():
        digest, name = line.split(None, 1)
        originals[Path(name.strip()).name] = digest
    # Nonrecursive directory bind exposes the original files below trial file mounts.
    view = '/run/fw-original-view-' + str(time.time_ns())
    shell('mkdir -m 700 ' + view + ' && mount --bind /usr/lib/firmware ' + view)
    try:
        for name, info in profile['files'].items():
            if shell('sha256sum ' + remote + '/' + name).split()[0] != info['sha256']:
                raise RuntimeError('Staged firmware changed')
            if shell('sha256sum ' + view + '/' + name).split()[0] != originals[name]:
                raise RuntimeError('Original firmware view differs from trial baseline')
            backup = args.backup_dir / name
            result = subprocess.run([args.adb, '-s', args.serial, 'pull', view + '/' + name, str(backup)],
                                    capture_output=True, timeout=40)
            if result.returncode or hashlib.sha256(backup.read_bytes()).hexdigest() != originals[name]:
                raise RuntimeError('Original firmware backup failed')
            report['files'][name] = {'original_sha256': originals[name], 'installed_sha256': info['sha256']}
        metadata = '/usr/share/uz801/modem-firmware-profile.json'
        old_metadata = shell('if test -f ' + metadata + '; then base64 ' + metadata + '; fi')
        if old_metadata:
            (args.backup_dir / 'previous-profile.json').write_bytes(base64.b64decode(old_metadata))
        report['status'] = 'all-original-files-backed-up-and-verified'
        save()
        print('All original firmware files backed up and hash-verified', flush=True)
    finally:
        shell('umount ' + view)
    identity()
    if shell('cat /proc/sys/kernel/random/boot_id') != boot:
        raise RuntimeError('Device rebooted during backup')
    shell('systemctl stop uz801-select-sim.service ModemManager.service')
    stop_modem()
    for destination in reversed(mounted):
        shell('umount ' + destination)
    report['status'] = 'installing; modem stopped; see verified rollback files on failure'
    save()
    finish_install(args, profile, trial, report, shell, before_nv)


if __name__ == '__main__':
    main()
