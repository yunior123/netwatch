#!/usr/bin/env python3
"""Live packet capture using raw BPF socket on macOS.
No root required if user has /dev/bpf access.
Writes to capture.pcap in tcpdump-compatible format."""
import os, struct, sys, time, fcntl

ROOT = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(ROOT, "data")
PCAP = os.path.join(DATA, "capture.pcap")

BPF_DEV = "/dev/bpf0"

# PCAP global header
PCAP_MAGIC = 0xa1b2c3d4
PCAP_VER_MAJOR = 2
PCAP_VER_MINOR = 4
PCAP_THISZONE = 0
PCAP_SIGFIGS = 0
PCAP_SNAPLEN = 128
PCAP_LINKTYPE = 1  # LINKTYPE_ETHERNET

def open_bpf():
    fd = os.open(BPF_DEV, os.O_RDWR)
    # Set snaplen
    buf = struct.pack("I", PCAP_SNAPLEN)
    fcntl.ioctl(fd, 0x80044267, buf)  # BIOCSETSNAPLEN
    # Set immediate mode (no buffering)
    buf = struct.pack("I", 1)
    fcntl.ioctl(fd, 0x80044266, buf)  # BIOCIMMEDIATE
    # Set timeout 100ms
    buf = struct.pack("I", 100)
    fcntl.ioctl(fd, 0x80044268, buf)  # BIOCSRTIMEOUT
    return fd

def attach_filter(fd, iface):
    """Attach interface to BPF device"""
    try:
        ifreq = struct.pack("16sH", iface.encode(), 0) + b'\x00' * 14
        fcntl.ioctl(fd, 0x80204200, ifreq)  # BIOCSETIF
    except Exception as e:
        print(f"warning: could not set interface: {e}", file=sys.stderr)

def write_pcap_header(f):
    f.write(struct.pack("<IHHiIII",
        PCAP_MAGIC, PCAP_VER_MAJOR, PCAP_VER_MINOR,
        PCAP_THISZONE, PCAP_SIGFIGS, PCAP_SNAPLEN, PCAP_LINKTYPE))

def write_pcap_packet(f, ts, pkt):
    ts_sec = int(ts)
    ts_usec = int((ts - ts_sec) * 1e6)
    incl_len = len(pkt)
    f.write(struct.pack("<IIII", ts_sec, ts_usec, incl_len, incl_len))
    f.write(pkt)
    f.flush()

def main():
    os.makedirs(DATA, exist_ok=True)
    iface = sys.argv[1] if len(sys.argv) > 1 else "en0"

    print(f"bpf_capture: opening {BPF_DEV} on {iface}")
    fd = open_bpf()
    attach_filter(fd, iface)

    with open(PCAP, "wb") as f:
        write_pcap_header(f)
        print(f"bpf_capture: writing to {PCAP}")
        while True:
            try:
                data = os.read(fd, 65535)
                if data:
                    write_pcap_packet(f, time.time(), data)
            except KeyboardInterrupt:
                break
            except OSError:
                time.sleep(0.1)

    os.close(fd)

if __name__ == "__main__":
    main()
