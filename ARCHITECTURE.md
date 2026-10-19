# Image architecture

The maintained image is assembled by `rootfs/build.sh` and customized by `rootfs/chroot.sh`. The workflow is `.github/workflows/build.yml`.

| Component | Ownership |
| --- | --- |
| Debian user space | debootstrap and Debian packages |
| Boot image, kernel and modules | External community kernel release assets; verify compatibility when updating |
| Qualcomm firmware | Dependency package referenced by the build |
| USB Gadget / ADB / board startup / disk expansion | OpenStick utility package; inspect its actual installed files |
| Preferred SIM selector | This repository's `rootfs/overlay/` |
| CID / IMEI / NV / recovery backups | Private per-device workspace; never part of the public image |

`openstick-gc-startup.service` starts the current USB implementation using `openstick-gc-manager.sh`, `gc` and `adbd`. Older documents referred to `linux-adbd-utils.service` and `linux-usb-gadget`; their names must not be assumed to describe the current dependency package.

Generic SIM selection uses ModemManager. It does not assume an LED path is an electrical SIM switch. Board-specific startup supplied by upstream packages is separate and must be inspected before changing it.

See `docs/CUSTOMIZATIONS.md` for maintained source, deployment behavior and validation criteria.
