#!/usr/bin/env bash
# NZOYI — restauration du lab aux snapshots propres (KVM/libvirt).
#
# Remet chaque VM du banc à son snapshot de référence après un run, pour que le
# lab soit reproductible (critère d'acceptation : lab restaurable).
#
# Usage :
#   scripts/restore_lab.sh                      # VMs + snapshots par défaut
#   NZOYI_LAB_VMS="ubuntu-target win-dc" \
#   NZOYI_LAB_SNAPSHOT=clean scripts/restore_lab.sh
#
# Variables :
#   NZOYI_LAB_VMS       liste de domaines libvirt (défaut: "ubuntu-target")
#   NZOYI_LAB_SNAPSHOT  nom du snapshot de référence (défaut: "clean")
#   NZOYI_LIBVIRT_URI   URI libvirt (défaut: qemu:///system)
set -uo pipefail

VMS="${NZOYI_LAB_VMS:-ubuntu-target}"
SNAP="${NZOYI_LAB_SNAPSHOT:-clean}"
URI="${NZOYI_LIBVIRT_URI:-qemu:///system}"

if ! command -v virsh >/dev/null 2>&1; then
  echo "[!] virsh introuvable — installe libvirt-clients." >&2
  exit 1
fi

fail=0
for vm in $VMS; do
  echo "[*] $vm : restauration du snapshot '$SNAP'…"
  if ! virsh -c "$URI" snapshot-list "$vm" --name 2>/dev/null | grep -qx "$SNAP"; then
    echo "  [!] snapshot '$SNAP' absent pour '$vm' — ignoré." >&2
    fail=1
    continue
  fi
  # Reset dur puis retour au snapshot propre.
  virsh -c "$URI" destroy "$vm" >/dev/null 2>&1 || true
  if virsh -c "$URI" snapshot-revert "$vm" "$SNAP" --running; then
    echo "  [+] $vm restauré et redémarré."
  else
    echo "  [!] échec de la restauration de '$vm'." >&2
    fail=1
  fi
done

if [ "$fail" -eq 0 ]; then
  echo "[+] Lab restauré."
else
  echo "[!] Lab partiellement restauré (voir erreurs ci-dessus)." >&2
fi
exit "$fail"
