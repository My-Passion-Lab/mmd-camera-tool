# vmd_writer.py
import struct

# Camera VMD interpolation (24 bytes)
# Format: (x1, x2, y1, y2) x 6 parameters
#   Parameter order: X, Y, Z, Rotation, Distance, FOV
#   P1 = (x1/127, y1/127)  P2 = (x2/127, y2/127)
#
# Linear:  x1=20,  x2=107, y1=20,  y2=107  -> diagonal (P1=(0.16,0.16) P2=(0.84,0.84))
# S-curve: x1=44,  x2=85,  y1=6,   y2=121  -> slow-fast-slow (P1=(0.35,0.05) P2=(0.67,0.95))
#   (= values from actual manually-created MMD camera VMD with S-curve)
INTERP_LINEAR  = bytes([20, 107, 20, 107] * 6)
INTERP_S_CURVE = bytes([44,  85,  6, 121] * 6)


def write_vmd(camera_frames: list) -> bytes:
    buf = bytearray()

    # Header (30 bytes)
    buf += b"Vocaloid Motion Data 0002"
    buf += b"\x00" * 5

    # Model name (20 bytes) - camera VMD uses this name
    model_name = "カメラ・照明".encode("shift-jis")
    buf += model_name.ljust(20, b"\x00")

    # Bone frame count = 0
    buf += struct.pack("<I", 0)

    # Morph frame count = 0
    buf += struct.pack("<I", 0)

    # Camera frame count
    buf += struct.pack("<I", len(camera_frames))

    # Camera frames (61 bytes each)
    # +0  frame_no (4) / +4  distance (4) / +8  pos_xyz (12) / +20 rot_xyz (12)
    # +32 interp (24)  / +56 fov (4)       / +60 perspective (1)
    for f in camera_frames:
        interp = INTERP_S_CURVE if f.get("s_curve", False) else INTERP_LINEAR
        buf += struct.pack("<I",   f["frame"])
        buf += struct.pack("<f",   f["distance"])
        buf += struct.pack("<fff", f["pos_x"], f["pos_y"], f["pos_z"])
        buf += struct.pack("<fff", f["rot_x"], f["rot_y"], f["rot_z"])
        buf += interp
        buf += struct.pack("<I",   f["fov"])
        buf += struct.pack("<B",   0)

    # Light frame count = 0
    buf += struct.pack("<I", 0)

    # Shadow frame count = 0
    buf += struct.pack("<I", 0)

    return bytes(buf)
