# vmd_reader.py
import struct, math

# ── ボーン名の正規化（IK表記揺れのみ対応）──
# 漢字・ひらがな・カタカナには一切手を加えない
_IK_VARIANTS = [
    ("左足IK",  "左足ＩＫ"),
    ("左足ik",  "左足ＩＫ"),
    ("左足Ik",  "左足ＩＫ"),
    ("左足iK",  "左足ＩＫ"),
    ("左足ｉｋ", "左足ＩＫ"),
    ("右足IK",  "右足ＩＫ"),
    ("右足ik",  "右足ＩＫ"),
    ("右足Ik",  "右足ＩＫ"),
    ("右足iK",  "右足ＩＫ"),
    ("右足ｉｋ", "右足ＩＫ"),
]
_IK_TABLE = {v: n for v, n in _IK_VARIANTS}


def _normalize(raw: bytes) -> str:
    """
    VMDのボーン名バイト列を正規化する。
    やること: Shift-JIS デコード + IK表記揺れの統一のみ。
    漢字・かな・カタカナには一切触れない。
    """
    name = raw.split(b"\x00")[0].decode("shift-jis", errors="ignore")
    return _IK_TABLE.get(name, name)


# 位置を読み込むボーン
_POS_BONES = {
    "全ての親", "グルーブ", "センター",
    "左足ＩＫ", "右足ＩＫ",
    "上半身",
    "下半身", "腰",
    "右手首", "左手首",
    "右足首", "左足首",
    "右足",   "左足",
}

# 回転（クォータニオン）も読み込むボーン
_ROT_BONES = {"頭", "上半身", "下半身", "右腕", "左腕"}  # 手クロースアップ検知用


def read_vmd_bones(data: bytes) -> dict:
    """
    VMDを解析してボーンデータを返す。
    {
      "ボーン名":      {frame: (x,y,z)},          # 位置
      "ボーン名_rot":  {frame: (qx,qy,qz,qw)},   # 回転
    }
    """
    pos        = 30 + 20
    bone_count = struct.unpack_from("<I", data, pos)[0]
    pos       += 4
    bones      = {}

    for _ in range(bone_count):
        raw  = data[pos:pos+15];  pos += 15
        name = _normalize(raw)

        frm  = struct.unpack_from("<I",    data, pos)[0];  pos += 4
        xyz  = struct.unpack_from("<fff",  data, pos);     pos += 12
        quat = struct.unpack_from("<ffff", data, pos);     pos += 16
        pos += 64   # 補間曲線

        if name in _POS_BONES:
            bones.setdefault(name, {})[frm] = xyz
        if name in _ROT_BONES:
            bones.setdefault(name + "_rot", {})[frm] = quat

    return bones


def get_total_frames(bones: dict) -> int:
    m = 0
    for fd in bones.values():
        if fd:
            m = max(m, max(fd.keys()))
    return m


def get_detected_bones_report(bones: dict) -> dict:
    """
    app.py のログ表示用。
    位置ボーンと回転ボーンの検出フレーム数を返す。
    {
      "pos": {"センター": 1234, "左足ＩＫ": 567, ...},
      "rot": {"頭": 890, "上半身": 234, ...},
    }
    """
    pos_report = {}
    rot_report = {}
    for key, fd in bones.items():
        if key.endswith("_rot"):
            rot_report[key.replace("_rot", "")] = len(fd)
        else:
            pos_report[key] = len(fd)
    return {"pos": pos_report, "rot": rot_report}


def _lerp_val(fd: dict, frame: int) -> tuple:
    fl = sorted(fd.keys())
    if frame in fd:     return fd[frame]
    if frame <= fl[0]:  return fd[fl[0]]
    if frame >= fl[-1]: return fd[fl[-1]]
    a = max(f for f in fl if f <= frame)
    b = min(f for f in fl if f >= frame)
    t = (frame - a) / (b - a)
    p, n = fd[a], fd[b]
    return tuple(p[i] + (n[i] - p[i]) * t for i in range(len(p)))


def lerp_pos(bones: dict, name: str, frame: int):
    if name not in bones:
        return None
    return _lerp_val(bones[name], frame)


def lerp_quat(bones: dict, name: str, frame: int):
    key = name + "_rot"
    if key not in bones:
        return None
    fd = bones[key]
    fl = sorted(fd.keys())
    if frame in fd:     return fd[frame]
    if frame <= fl[0]:  return fd[fl[0]]
    if frame >= fl[-1]: return fd[fl[-1]]
    a = max(f for f in fl if f <= frame)
    b = min(f for f in fl if f >= frame)
    t = (frame - a) / (b - a)
    p, n = fd[a], fd[b]
    dot = sum(p[i]*n[i] for i in range(4))
    if dot < 0:
        n = tuple(-v for v in n); dot = -dot
    dot = min(1.0, dot)
    if dot > 0.9995:
        q = tuple(p[i] + (n[i]-p[i])*t for i in range(4))
    else:
        th = math.acos(dot); s = math.sin(th)
        q  = tuple(math.sin((1-t)*th)/s * p[i]
                   + math.sin(t*th)/s * n[i] for i in range(4))
    ln = math.sqrt(sum(v*v for v in q))
    return tuple(v/ln for v in q) if ln > 0 else q


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# ① 真のモデル位置（3ボーン合算）
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━
def get_model_pos(bones: dict, frame: int) -> tuple:
    """全ての親 + グルーブ + センター の合算XYZ"""
    x = y = z = 0.0
    for b in ("全ての親", "グルーブ", "センター"):
        p = lerp_pos(bones, b, frame)
        if p:
            x += p[0]; y += p[1]; z += p[2]
    return x, y, z


def _rot_angle(bones: dict, bone_name: str, frame: int,
               span: int = 5) -> float:
    """指定ボーンの回転速度（rad/frame）"""
    qa = lerp_quat(bones, bone_name, max(0, frame - span))
    qb = lerp_quat(bones, bone_name, frame + span)
    if qa is None or qb is None:
        return 0.0
    dot = min(1.0, abs(sum(qa[i]*qb[i] for i in range(4))))
    return 2.0 * math.acos(dot) / (span * 2)


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# ③ セーフティ判定（閾値を大幅緩和）
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━

def get_safety(bones: dict, frame: int, char_h: float) -> dict:
    """
    セーフティ判定（③ あべこべ現象の修正版）

    ★ 方針 ★
    その場でのダンス動作（腰振り・ステップ）→ pull 小さく（アップを許可）
    本当に危険な状態（挙手・激しい上下動）   → pull 大きく（引き）
    """
    mx, my, mz = get_model_pos(bones, frame)
    head_y     = char_h * 0.88 + my

    # ── 激しい上下動（ジャンプ・完全に座る）──
    # 緩和: 通常のステップでは反応しない（0.20以上のみ）
    SPAN      = 8
    pa        = get_model_pos(bones, max(0, frame - SPAN))
    pb        = get_model_pos(bones, frame + SPAN)
    vert_v    = abs(pb[1] - pa[1]) / (SPAN * 2)
    vert_pull = min(22.0, (vert_v - 0.20) / 0.10 * 18.0) \
                if vert_v > 0.20 else 0.0

    # ── 挙手（手首が頭よりかなり高い）──
    # 頭より char_h*0.15 以上高い時だけ反応
    hand_pull = 0.0
    for b in ("右手首", "左手首"):
        lp = lerp_pos(bones, b, frame)
        if lp is None:
            continue
        hand_y = lp[1] + my
        excess = hand_y - head_y - char_h * 0.15
        if excess > 0:
            hand_pull = max(hand_pull, min(30.0, excess * 7.0))

    # ── 足IKの大移動（ジャンプ・大股）のみ ──
    # 緩和: char_h*0.7 以上（大股・ジャンプのみ反応）
    ik_pull = 0.0
    for b in ("左足ＩＫ", "右足ＩＫ"):
        lp = lerp_pos(bones, b, frame)
        if lp is None:
            continue
        move = math.sqrt(lp[0]**2 + lp[1]**2 + lp[2]**2)
        if move > char_h * 0.70:
            ik_pull = max(ik_pull,
                          min(20.0, (move - char_h*0.70) / char_h * 30.0))

    # 腰振り・ステップは pull に含めない（camera_core の _classify_action で処理）
    pull = max(vert_pull, hand_pull, ik_pull)

    return {
        "pull":    pull,
        "is_busy": pull > 15.0,
    }

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# ② 大移動カット分割点の検知
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━
def find_cut_points(bones: dict,
                    f_start: int, f_end: int,
                    char_h: float,
                    threshold: float = 2.0) -> list:
    """
    モデルの「本当に大きな移動」だけを検知。
    threshold を 1.2→2.0 に緩和して誤検知を防ぐ。
    """
    SPAN   = 4
    result = []
    last   = f_start - 30

    for f in range(f_start + SPAN, f_end - SPAN, 2):
        pa  = get_model_pos(bones, f - SPAN)
        pb  = get_model_pos(bones, f + SPAN)
        spd = math.sqrt(sum((pb[i]-pa[i])**2 for i in range(3))) / (SPAN*2)

        # 足IKも確認（大股・ジャンプのみ）
        ik_spd = 0.0
        for b in ("左足ＩＫ", "右足ＩＫ"):
            ia = lerp_pos(bones, b, f - SPAN)
            ib = lerp_pos(bones, b, f + SPAN)
            if ia and ib:
                s = math.sqrt(sum((ib[i]-ia[i])**2
                                  for i in range(3))) / (SPAN*2)
                ik_spd = max(ik_spd, s * 0.5)  # 足IKは重みを下げる

        if max(spd, ik_spd) > threshold and f - last > 20:
            result.append(f)
            last = f

    return result