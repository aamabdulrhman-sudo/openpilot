#!/usr/bin/env python3
"""
FreePilots eSIM & Cellular Carrier Tool for Comma Four / TICI
Allows users to install custom eSIM profiles (STC, Mobily, Zain, etc.)
and bypass Comma Prime subscription completely.
"""
import sys
import os

from openpilot.common.params import Params
from openpilot.system.hardware.tici.lpa import TiciLPA

def print_help():
    print("FreePilots eSIM & Carrier Manager for Comma Four")
    print("------------------------------------------------")
    print("Usage:")
    print("  python3 tools/esim.py list")
    print("  python3 tools/esim.py install <LPA_STRING> [nickname]")
    print("  python3 tools/esim.py switch <ICCID>")
    print("  python3 tools/esim.py apn <APN_NAME>")
    print("  python3 tools/esim.py status")
    print("")
    print("Examples:")
    print("  python3 tools/esim.py install 'LPA:1$smdp.io$XXXXX' MySTC")
    print("  python3 tools/esim.py apn 'jawaawy.net.sa'")

def main():
    if len(sys.argv) < 2:
        print_help()
        sys.exit(1)

    cmd = sys.argv[1].lower()
    params = Params()

    try:
        lpa = TiciLPA()
    except Exception as e:
        print(f"Error initializing modem LPA: {e}")
        sys.exit(1)

    if cmd == "list":
        print("Installed eSIM Profiles:")
        profiles = lpa.list_profiles()
        if not profiles:
            print("  (No eSIM profiles found)")
        for p in profiles:
            status = "ACTIVE" if p.enabled else "INACTIVE"
            print(f"  - ICCID: {p.iccid} | Provider: {p.provider or 'Unknown'} | Nickname: {p.nickname or 'N/A'} | [{status}]")

    elif cmd == "install":
        if len(sys.argv) < 3:
            print("Error: Missing LPA activation string. Example: python3 tools/esim.py install 'LPA:1$...'")
            sys.exit(1)
        lpa_str = sys.argv[2]
        nickname = sys.argv[3] if len(sys.argv) > 3 else "FreePilot-SIM"
        print(f"Downloading and installing eSIM profile: {nickname}...")
        lpa.download_profile(lpa_str, nickname)
        print("eSIM Profile installed successfully!")

    elif cmd == "switch":
        if len(sys.argv) < 3:
            print("Error: Missing ICCID. Run 'python3 tools/esim.py list' to see available ICCIDs.")
            sys.exit(1)
        iccid = sys.argv[2]
        print(f"Switching to profile {iccid}...")
        lpa.switch_profile(iccid)
        print("Switched successfully!")

    elif cmd == "apn":
        if len(sys.argv) < 3:
            print("Error: Missing APN. Example: python3 tools/esim.py apn 'jawaawy.net.sa'")
            sys.exit(1)
        apn = sys.argv[2]
        params.put("GsmApn", apn)
        params.put_bool("GsmRoaming", True)
        print(f"APN configured to: '{apn}' (Roaming: Enabled)")
        print("Restarting modem service to apply...")
        os.system("sudo systemctl restart comma-modem 2>/dev/null || pkill -SIGHUP -f system.hardware.tici.modem")
        print("Done! Cellular connection will initialize shortly.")

    elif cmd == "status":
        apn = params.get("GsmApn", encoding='utf-8') or "(default/carrier-provided)"
        roaming = params.get_bool("GsmRoaming")
        print(f"Current APN: {apn}")
        print(f"Roaming Allowed: {roaming}")
        profiles = lpa.list_profiles()
        active = [p for p in profiles if p.enabled]
        if active:
            print(f"Active eSIM: {active[0].iccid} ({active[0].provider or active[0].nickname or 'Custom'})")
        else:
            print("Active eSIM: None")

    else:
        print_help()

if __name__ == '__main__':
    main()
