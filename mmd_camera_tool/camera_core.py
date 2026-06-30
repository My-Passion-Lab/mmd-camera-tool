# camera_core.py  ── 根本修正版
# ルール① 打鍵: _write_pair で stray 削除 + XZ大移動の変曲点に例外ペア
# ルール② 構図: divisor 4.2〜6.0、FOV<27 では頭ボーン直接狙いに減衰
# ルール③ 感度: large_move 閾値 combined_hspd > 2.6
import math
from vmd_reader import get_model_pos, get_safety, lerp_pos, lerp_quat

MIN_DIST  = -22.0
LONG_DIST = -65.0

_DIST_FOV = [
    (15, 15), (22, 20), (30, 25),
    (40, 30), (52, 36), (65, 42), (80, 48),
]


def dist_to_fov(distance: float, fov_base: int) -> int:
    abs_d = abs(distance)
    if   abs_d <= _DIST_FOV[0][0]:  fov = float(_DIST_FOV[0][1])
    elif abs_d >= _DIST_FOV[-1][0]: fov = float(_DIST_FOV[-1][1])
    else:
        fov = float(_DIST_FOV[-1][1])
        for i in range(len(_DIST_FOV) - 1):
            d0, f0 = _DIST_FOV[i]
            d1, f1 = _DIST_FOV[i + 1]
            if d0 <= abs_d <= d1:
                fov = f0 + (f1 - f0) * (abs_d - d0) / (d1 - d0)
                break
    return int(max(10, min(120, fov * fov_base / 30.0)))


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# 【ルール②】構図: divisor と頭の画面位置の数学的関係
#
#   頭の画面上端からの割合 = 1/2 - 1/divisor
#     divisor=3.5 → 21%（上にはみ出す：NGの根本原因）
#     divisor=4.2 → 26%
#     divisor=6.0 → 33%（正しい1/3）
#
#   したがって divisor は大きいほど頭が下がる（画面中央寄り）。
#   FOVが狭い（world_h が極小）アップ時は、
#   head_y そのものを狙う方が安全なため、offset を減衰させる。
#
#   実装:
#     base divisor: 4.2(FOV≤20) 〜 6.0(FOV≥35) リニア補間
#     narrow blend: FOV=15 → offset=0（頭直接）, FOV=27 → offset フル
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
def _pos_y(frame: int, bones: dict, char_h: float, dist: float, fov_deg: float,
           composition: str = "head", use_face_bow: bool = True) -> float:
    mx, my, mz = get_model_pos(bones, frame)

    # ── 距離スケール補正 k オフセット（body/head 共通）──
    # 基準距離 DIST_REF=22 で k を較正し、遠距離では (22/dist) で縮小。
    # 例: FOV15/dist65 → offset=1.61 (旧offset=14.07 で過大だった問題を修正)
    #     FOV30/dist90 → offset=0.18
    DIST_REF    = 22.0
    world_h_ref = 2.0 * DIST_REF * math.tan(math.radians(fov_deg) / 2.0)
    dist_scale  = DIST_REF / max(1.0, abs(dist))

    # 区間線形補間 k（単調減少: FOV広がるにつれオフセット縮小）
    # FOV15:0.85 → FOV20:0.51 → FOV27:0.10 → FOV32:0.010
    # ※ FOV15は dist_scale キャップ(22/18)を追加適用
    if fov_deg <= 15.0:
        k = 0.67                         # 実測較正: dist22=-1.05, dist14=-1.50, dist16=-1.00
        dist_scale = min(dist_scale, DIST_REF / 18.0)  # dist<18 の過大補正防止
    elif fov_deg <= 20.0:
        t = (fov_deg - 15.0) / 5.0
        k = 0.67 + t * (0.47 - 0.67)   # 0.67→0.47（FOV17≈0.59: dist18 -1.00 実測合致）
    elif fov_deg <= 27.0:
        t = (fov_deg - 20.0) / 7.0
        k = 0.38 + t * (0.10 - 0.38)   # 0.38→0.10
    elif fov_deg <= 32.0:
        t = (fov_deg - 27.0) / 5.0
        k = 0.10 + t * (0.010 - 0.10)  # 0.10→0.010
    else:
        k = 0.010

    k_offset = world_h_ref * k * dist_scale

    # ── body モード: 全身構図（締めカット等）──
    # char_h × 80% (胸上あたり) を基準とし k_offset を加算。
    # 旧 0.45 → 0.80 に変更: head comp との Y 乖離を 6→1 単位に縮小。
    # 実測: dist=90/FOV30 standing → body≈12.8 vs head≈12.9 (差0.1)
    #       dist=65/FOV30 my=-1.3  → body≈11.6 vs 理想 11.83 (差0.2)
    if composition == "body":
        return my + char_h * 0.80 + k_offset

    # ── foot モード: 足元アングル（FOV60 ローアングル）──
    # char_h × 63% → pos_y ≈ 10.3（靴まで見せる位置）
    if composition == "foot":
        return my + char_h * 0.63 + k_offset

    # ── head モード（デフォルト）: 座り・前傾補正を含む ──
    # my=-1 以下から補正開始, my=-16 で最大 (h_mult: 0.85→0.73)
    h_mult = 0.85
    if my < -1.0:
        sit_t  = min(1.0, (-my - 1.0) / 15.0)
        h_mult = 0.85 - sit_t * 0.12
    head_y = my + char_h * h_mult

    # 前かがみ補正（MMD では前傾 = 負X回転 → max(0, -q[0]) で量を取得）
    lean_sum = 0.0
    for bone in ("腰", "上半身", "上半身2"):
        q = lerp_quat(bones, bone, frame)
        if q is not None:
            lean_sum += max(0.0, -q[0])
    lean_drop = char_h * min(0.50, (lean_sum ** 1.5) * 0.80)  # 幾何較正: 90°=8単位, 60°=4.5単位
    head_y -= lean_drop

    # 頭・首の下向き補正（カット開始/終了フレームのみ適用）
    # Y追従中間フレームでは use_face_bow=False にして連続性を保つ
    if use_face_bow:
        bow_total = 0.0
        for bone in ("首", "頭"):
            q = lerp_quat(bones, bone, frame)
            if q is not None:
                bow_total += max(0.0, -q[0])      # 負X = 前屈（下向き）
        face_drop = char_h * 0.15 * min(1.0, bow_total / 0.4)
        head_y -= face_drop

    return head_y + k_offset


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# セーフティ補助: 万歳ポーズ
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
def _banzai_pull(bones: dict, frame: int, char_h: float) -> float:
    _, my, _ = get_model_pos(bones, frame)
    head_y   = my + char_h * 0.85
    extra    = 0.0
    for b in ("右手首", "左手首"):
        lp = lerp_pos(bones, b, frame)
        if lp is None:
            continue
        excess = lp[1] + my - head_y - char_h * 0.10
        if excess > 0:
            extra = max(extra, min(35.0, excess * 9.0))
    return extra


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# セーフティ補助: 手が顔付近にある時の引き
# アップカット（base_dist < 30）限定で適用。
# 手首Y ≈ 頭Y（±18%以内）かつ手のXZ局所距離が体幅以内 → 8単位追加引き
# → 手と顔が両方フレームに収まるよう自動調整
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
def _hand_face_pull(bones: dict, frame: int, char_h: float) -> float:
    _, my, _ = get_model_pos(bones, frame)
    head_y = my + char_h * 0.85
    extra  = 0.0
    for b in ("右手首", "左手首"):
        lp = lerp_pos(bones, b, frame)
        if lp is None:
            continue
        hand_world_y = lp[1] + my
        if abs(hand_world_y - head_y) < char_h * 0.18:   # 顔Y範囲内
            hand_xz = math.sqrt(lp[0] ** 2 + lp[2] ** 2)
            if hand_xz < char_h * 0.40:                   # 腕を横に広げていない
                extra = max(extra, 8.0)
    return extra


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# 手クロースアップ区間スキャン
# _hand_face_pull を 3F 間隔で全フレームスキャンし、
# 手が顔に近い連続区間 [(start, end), ...] を返す。
# generate_cuts() の冒頭で一度だけ呼び出して使い回す。
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
def _build_hand_intervals(bones: dict, total_frames: int, char_h: float) -> list:
    """手首が顔付近に来るフレーム区間 [(start, end), ...] を返す。"""
    SCAN_STEP = 3
    MIN_LEN   = 8   # 短すぎる誤検知を無視
    intervals  = []
    in_hand    = False
    h_start    = 0
    for f in range(0, total_frames + 1, SCAN_STEP):
        near = _hand_face_pull(bones, f, char_h) > 0
        if near and not in_hand:
            in_hand = True; h_start = f
        elif not near and in_hand:
            in_hand = False
            if f - h_start >= MIN_LEN:
                intervals.append((h_start, f))
    if in_hand and total_frames - h_start >= MIN_LEN:
        intervals.append((h_start, total_frames))
    return intervals


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# 【ルール③】動作分類
#   combined_hspd > 2.6: お尻振りは無視、横ステップには反応
#   vspd > 0.40: 小さな上下動は無視
#   検知ボーン: 左足ＩＫ・右足ＩＫ・上半身・腰
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
def _classify(bones: dict, frame: int, char_h: float) -> str:
    SPAN = 6
    pa   = get_model_pos(bones, max(0, frame - SPAN))
    pb   = get_model_pos(bones, frame + SPAN)
    hspd = math.sqrt((pb[0]-pa[0])**2 + (pb[2]-pa[2])**2) / (SPAN * 2)
    vspd = abs(pb[1] - pa[1]) / (SPAN * 2)

    extra_spd = 0.0
    foot_spd  = 0.0   # 足ＩＫのみの速度（歩き・ステップ検知用）
    for bone in ("左足ＩＫ", "右足ＩＫ", "上半身", "腰"):
        ia = lerp_pos(bones, bone, max(0, frame - SPAN))
        ib = lerp_pos(bones, bone, frame + SPAN)
        if ia and ib:
            s = math.sqrt(
                (ib[0]-ia[0])**2 + (ib[1]-ia[1])**2 + (ib[2]-ia[2])**2
            ) / (SPAN * 2)
            extra_spd = max(extra_spd, s)
            if "足ＩＫ" in bone:
                foot_spd = max(foot_spd, s)

    combined_hspd = hspd + extra_spd * 0.5

    def rs(bone):
        qa = lerp_quat(bones, bone, max(0, frame - SPAN))
        qb = lerp_quat(bones, bone, frame + SPAN)
        if not qa or not qb:
            return 0.0
        return 2.0 * math.acos(
            min(1.0, abs(sum(qa[i]*qb[i] for i in range(4))))
        ) / (SPAN * 2)

    yaw = rs("頭")
    hip = rs("下半身")

    if combined_hspd > 2.6 or vspd > 0.40: return "large_move"
    if foot_spd > 2.5:                      return "busy_feet"   # 歩き・ステップ → 引き

    # ── 蹴り・足上げ検知 ──
    # 足IKはワールドY座標で保存されるため、直接比較で「足が地面から離れているか」を判断。
    # 通常のジャンプ（グルーブY上昇）は 足IK.y ≈ 0 のまま → 検知しない（意図的）
    # キック・横キック・足上げジャンプ は 足IK.y が大きな正値になる → 検知してやや引く
    KICK_THRESH = 3.0   # 地面から 3 ユニット以上 = キック/足上げ判定
    max_foot_y  = 0.0
    for bone in ("左足ＩＫ", "右足ＩＫ"):
        ik = lerp_pos(bones, bone, frame)
        if ik is not None:
            max_foot_y = max(max_foot_y, ik[1])
    if max_foot_y > KICK_THRESH:
        return "kick"

    if yaw > 0.12:                          return "fast_rotate"
    if hip > 0.06 or yaw > 0.04:           return "dance"
    if extra_spd > 0.8:                     return "dance"
    return "normal"


def _xz_hspd(bones: dict, frame: int, span: int = 6) -> float:
    """
    全ての親＋グルーブ＋センター（3ボーン合算）の水平XZ移動速度。
    大移動の開始・終了検知専用。足IK・腰は含まない。
    """
    pa = get_model_pos(bones, max(0, frame - span))
    pb = get_model_pos(bones, frame + span)
    return math.sqrt((pb[0]-pa[0])**2 + (pb[2]-pa[2])**2) / (span * 2)


def _safe_dist(base: float, action: str,
               s_pull: float, banzai: float) -> float:
    if action in ("large_move", "fast_rotate"):
        dist = min(base, LONG_DIST)
    elif action == "busy_feet":
        dist = min(base, -42.0)           # 足が見えるよう引く
    elif action == "kick":
        dist = min(base, -45.0)           # キック・足上げ: やや引いて足まで見せる
    elif action == "dance":
        dist = max(min(base, MIN_DIST), -44.0)   # -35→-44: 複数カットが同距離に見える問題を解消
    else:
        dist = base
    pull = max(s_pull - 15.0 if s_pull > 15.0 else 0.0, banzai)
    if pull > 0:
        dist -= pull * (1.0 if abs(dist) < 50.0 else 0.6)
    return min(dist, MIN_DIST)


def _woffset(sdx: float, sdz: float, ry: float) -> tuple:
    if abs(ry) < 0.05:
        return 0.0, sdz
    return (sdx * math.cos(ry) - sdz * math.sin(ry),
            sdx * math.sin(ry) + sdz * math.cos(ry))


def build_frame(frame_no: int,
                bones: dict, char_h: float,
                base_dist: float,
                rx: float, ry: float, rz: float,
                fov_base: int,
                sdx: float = 0.0, sdz: float = 0.0,
                fov_override: int = None,
                composition: str = "head") -> dict:
    n      = max(0, frame_no)
    action = _classify(bones, n, char_h)
    safety = get_safety(bones, n, char_h)
    banzai     = _banzai_pull(bones, n, char_h)
    hand_face  = _hand_face_pull(bones, n, char_h) if abs(base_dist) < 30.0 else 0.0
    dist       = _safe_dist(base_dist, action, safety["pull"], max(banzai, hand_face))
    mx, my, mz = get_model_pos(bones, n)
    fov    = fov_override if fov_override is not None else dist_to_fov(dist, fov_base)
    pos_y  = _pos_y(n, bones, char_h, dist, fov, composition)
    wx, wz = _woffset(sdx, sdz, ry)
    return {
        "frame":    n,
        "distance": dist,
        "pos_x":    mx + wx,
        "pos_y":    pos_y,
        "pos_z":    mz + wz,
        "rot_x":    rx, "rot_y": ry, "rot_z": rz,
        "fov":      fov,
    }


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# 【ルール①】打鍵: 単発キーフレーム + XZ大移動でカット強制切り替え
#
# キーフレーム配置設計（単発1つずつ）:
#   カットA : frame cur  (距離d )  ←  カット入り ◆
#             frame end  (距離ed)  ←  カット抜け ◆
#   カットB : frame end+1(距離d2)  ←  カット入り ◆  ← ここで値が変わる = CUT!
#             frame end2 (距離ed2) ←  カット抜け ◆
#
#   → 境界は常に「前カット終◆」「次カット始◆」の 2点のみ。
#   → 各カット内は開始/終了の2点を MMD が補間 → なめらかな動き。
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
def generate_cuts(bones: dict,
                  char_h: float,
                  fov_base: int,
                  cut_defs: list,
                  total_frames: int,
                  final_rot_y: float = 0.0,
                  intro_cut: dict = None) -> list:
    seen = {}   # {frame_no: frame_dict}

    def _write(f_raw: int, d, rx, ry, rz, sdx, sdz, fov_ov=None, comp="head", py_off=0.0, s_curve=False):
        """単発キーフレームを1つ書く。fov_ov が指定されれば FOV を強制設定。"""
        f = max(0, min(f_raw, total_frames))
        seen[f] = build_frame(f, bones, char_h, d, rx, ry, rz, fov_base, sdx, sdz, fov_ov, comp)
        if py_off:
            seen[f]["pos_y"] += py_off
        if s_curve:
            seen[f]["s_curve"] = True

    def _write_cut_start(f_raw: int, d, rx, ry, rz, sdx, sdz, fov_ov=None, comp="head", py_off=0.0, s_curve=False):
        """
        カット開始フレーム専用: _safe_dist をバイパスし cut_defs の自然な距離で記録。
        large_move/busy_feet/kick 中でも前フレームとの距離差を保持し、
        ◆◆ が視覚的なカット変化として確実に見えるようにする。
        （カット中断後の次フレームでは通常の _safe_dist が動作するので安全性は保たれる）
        """
        f    = max(0, min(f_raw, total_frames))
        dist = d  # _safe_dist バイパス: 指定距離をそのまま使用
        fov  = fov_ov if fov_ov is not None else dist_to_fov(dist, fov_base)
        py   = _pos_y(f, bones, char_h, dist, fov, comp) + py_off
        mx, _, mz = get_model_pos(bones, f)
        wx, wz    = _woffset(sdx, sdz, ry)
        seen[f] = {
            "frame":    f,
            "distance": dist,
            "pos_x":    mx + wx,
            "pos_y":    py,
            "pos_z":    mz + wz,
            "rot_x":    rx, "rot_y": ry, "rot_z": rz,
            "fov":      fov,
        }
        if s_curve:
            seen[f]["s_curve"] = True

    def _write_y_locked(f_raw: int, locked_d, rx, ry, rz, sdx, sdz, fov_ov=None, py_off=0.0):
        """
        Y追従専用キーフレーム。
        distance を線形補間値に固定（_safe_dist をバイパス）することで
        ジャンプ・座り追従時にズームがガタつく問題を防ぐ。
        pos_y だけ実際のポーズから算出し、他は通常通り。
        """
        f = max(0, min(f_raw, total_frames))
        fov  = fov_ov if fov_ov is not None else dist_to_fov(locked_d, fov_base)
        py   = _pos_y(f, bones, char_h, locked_d, fov, use_face_bow=False) + py_off
        mx, _, mz = get_model_pos(bones, f)
        wx, wz    = _woffset(sdx, sdz, ry)
        seen[f] = {
            "frame":    f,
            "distance": locked_d,
            "pos_x":    mx + wx,
            "pos_y":    py,
            "pos_z":    mz + wz,
            "rot_x":    rx, "rot_y": ry, "rot_z": rz,
            "fov":      fov,
        }

    SCAN_STEP  = 4
    THRESHOLD  = 1.2

    # 静止判定パラメータ
    # STILL_SPEED: アイドル呼吸・微小揺れ(0.03前後)だけ「静止」と見なす。
    #              ゆっくりしたダンス(0.15〜0.25)は「動き」として通常カットを維持。
    STILL_SPEED = 0.12   # units/frame: これ以下なら「静止ポーズ」と判定
    STILL_MULT  = 3      # 静止時カット長の倍率（カット変化を1/3に減らす）

    def _model_avg_speed(f_a: int, f_b: int) -> float:
        """全身平均速度 (units/frame): センター・上半身・両手首の最大速度を返す。
        手がバタバタしているだけでも「動いている」と正しく判定できる。"""
        STEP  = 8
        limit = min(f_b, f_a + STEP * 20)
        max_spd = 0.0

        # センター（グローバル移動）
        prev_c = get_model_pos(bones, f_a)
        total, n = 0.0, 0
        for sf in range(f_a + STEP, limit + 1, STEP):
            curr_c = get_model_pos(bones, sf)
            total += math.sqrt((curr_c[0]-prev_c[0])**2 + (curr_c[1]-prev_c[1])**2 + (curr_c[2]-prev_c[2])**2)
            prev_c = curr_c; n += 1
        if n: max_spd = max(max_spd, total / (STEP * n))

        # 手首位置（腕がバタバタしているか）
        for bone in ("右手首", "左手首"):
            prev_b = lerp_pos(bones, bone, f_a)
            if prev_b is None: continue
            total, n = 0.0, 0
            for sf in range(f_a + STEP, limit + 1, STEP):
                curr_b = lerp_pos(bones, bone, sf)
                if curr_b is None: break
                total += math.sqrt((curr_b[0]-prev_b[0])**2 + (curr_b[1]-prev_b[1])**2 + (curr_b[2]-prev_b[2])**2)
                prev_b = curr_b; n += 1
            if n: max_spd = max(max_spd, total / (STEP * n))

        # 上半身・上半身2の回転速度（体幹の傾きやひねりを検知）
        # 上半身は回転ボーンなので位置ではなくクォータニオンで計測する
        for bone in ("上半身", "上半身2"):
            prev_q = lerp_quat(bones, bone, f_a)
            if prev_q is None: continue
            total, n = 0.0, 0
            for sf in range(f_a + STEP, limit + 1, STEP):
                curr_q = lerp_quat(bones, bone, sf)
                if curr_q is None: break
                dot = max(-1.0, min(1.0, abs(sum(prev_q[i] * curr_q[i] for i in range(4)))))
                rot_rad = 2 * math.acos(dot)
                total += rot_rad
                prev_q = curr_q; n += 1
            # char_h でスケーリングして位置速度と同オーダーに合わせる
            if n: max_spd = max(max_spd, total / (STEP * n) * char_h)

        return max_spd

    # ── イントロ静止検知 ──
    # intro_cut が指定されていれば、曲冒頭にモデルが静止している間は
    # 単一のワイドショットを使用しカット頻発を防ぐ。
    # STILL_THRESH 未満の速度が INTRO_MIN_FRAMES 以上続いた場合に適用。
    INTRO_STILL_THRESH = 0.10   # units/frame 以下 = 静止（呼吸・揺れは無視）
    INTRO_MIN_FRAMES   = 40     # これより短い静止では適用しない

    cur     = 0
    def_idx = 0

    if intro_cut is not None:
        motion_start = 0
        found_motion = False
        for sf in range(16, min(total_frames, 700), 8):
            if _model_avg_speed(max(0, sf - 16), sf) > INTRO_STILL_THRESH:
                motion_start = max(0, sf - 16)
                found_motion = True
                break
        if found_motion and motion_start >= INTRO_MIN_FRAMES:
            ic     = intro_cut
            ic_rx  = ic.get("rot_x", -0.04)
            ic_ry  = ic.get("rot_y", 0.0)
            ic_rz  = ic.get("rot_z", 0.0)
            ic_fov = ic.get("fov_override", None)
            ic_cmp = ic.get("composition", "body")
            ic_ed  = ic.get("end_distance", ic["distance"])
            _write_cut_start(0, ic["distance"], ic_rx, ic_ry, ic_rz, 0, 0, ic_fov, ic_cmp)
            _write(motion_start, ic_ed, ic_rx, ic_ry, ic_rz, 0, 0, ic_fov, ic_cmp)
            cur = motion_start + 1

    skip_start = False   # 強制カット後は開始フレームをスキップ

    # 手クロースアップ区間の事前スキャン（全フレーム1回のみ実行）
    hand_intervals = _build_hand_intervals(bones, total_frames, char_h)
    hand_iv_idx    = 0   # 次にチェックすべき区間ポインタ（前進のみ）

    while cur <= total_frames:
        cd  = cut_defs[def_idx % len(cut_defs)]
        d      = cd["distance"]
        ed     = cd.get("end_distance", d)
        rx     = cd["rot_x"]; ry = cd["rot_y"]; rz = cd["rot_z"]
        end_rx = cd.get("end_rot_x", rx)         # 終端 rot_x（省略で始端と同じ）
        end_ry = cd.get("end_rot_y", ry)         # 終端 rot_y（横流し・回り込み用）
        sdx    = cd.get("screen_dx", 0.0); sdz = cd.get("screen_dz", 0.0)
        fov_ov = cd.get("fov_override", None)   # FOV強制指定（Noneなら自動）
        comp   = cd.get("composition", "head")   # 構図モード: "head"(default) / "body"
        py_off = cd.get("pos_y_offset", 0.0)     # カメラ中心Y の固定オフセット（単位）
        s_curve = cd.get("s_curve", False)       # Sカーブ補間（ドリフトモード用）

        base_len   = cd["length"]
        end        = min(cur + base_len - 1, total_frames)

        # ── 開始フレーム（_safe_dist バイパス: 自然距離でカット境界を可視化）──
        # force_start=True のカットは same_next でスキップされても単独 ◆ を強制書き込み
        if not skip_start or cd.get("force_start", False):
            _write_cut_start(cur, d, rx, ry, rz, sdx, sdz, fov_ov, comp, py_off, s_curve)
        skip_start = False

        # ── 大移動検知 ──
        # スキャン除外条件:
        #   ・引きカット（avg_dist >= 45）: 視覚的にXZ移動が目立たない
        #   ・短いカット（base_len < 30）: 意図した短尺クロースアップを潰さない
        #     ㉑(length=20)など短尺カット開始直後にXZ発火→MIN_CUT_SPANで削除→
        #     後続の同dist/fovカットと直結してフラッシュが起きるのを防ぐ
        switch_f = None
        avg_dist_scan = (abs(d) + abs(ed)) / 2.0
        if avg_dist_scan < 45.0 and base_len >= 30:
            for scan_f in range(cur + 4, end - 3, SCAN_STEP):
                if _xz_hspd(bones, scan_f) > THRESHOLD:
                    switch_f = scan_f
                    break

        # ── 手クロースアップ検知 ──
        # 過去の区間をスキップ
        while hand_iv_idx < len(hand_intervals) and hand_intervals[hand_iv_idx][1] <= cur:
            hand_iv_idx += 1
        hand_switch_f = None
        if hand_iv_idx < len(hand_intervals):
            hi_s, hi_e = hand_intervals[hand_iv_idx]
            if hi_s < end:   # この区間は現カット内に開始する
                hand_switch_f = max(cur, hi_s)
                hand_iv_idx  += 1   # 消費済みにする

        if hand_switch_f is not None and (switch_f is None or hand_switch_f <= switch_f):
            # ── 顔クロースアップ挿入 ──
            HAND_FOV      = 20
            HAND_DIST     = -18.0
            HAND_LEN      = 35
            _MIN_SPAN     = 10
            if hand_switch_f - cur > _MIN_SPAN:
                _sw_t = min(1.0, max(0.0, (hand_switch_f - 1 - cur) / max(1, end - cur)))
                _sw_d = d + (ed - d) * _sw_t
                _write(hand_switch_f - 1, _sw_d, rx, ry, rz, sdx, sdz, fov_ov, comp, py_off)
            else:
                seen.pop(cur, None)   # 短すぎる → 開始フレームを取り消す
            hc_end = min(hand_switch_f + HAND_LEN - 1, total_frames)
            _write_cut_start(hand_switch_f, HAND_DIST, -0.03, 0.0, 0.0, 0.0, 0.0, HAND_FOV, "head")
            _write(hc_end,         HAND_DIST, -0.03, 0.0, 0.0, 0.0, 0.0, HAND_FOV, "head")
            def_idx   += 1   # 現カット定義はスキップ
            cur        = hc_end + 1
            skip_start = True

        elif switch_f is not None:
            # 短すぎるカット対策（◆◆◆◆防止）
            # XZ検知がカット開始から MIN_CUT_SPAN フレーム以内に発火した場合、
            # 開始フレームと終了フレームが近接して同一パラメータの◆◆◆◆を生成する。
            # → 開始フレームを削除し、次カットの開始だけ残す。
            MIN_CUT_SPAN = 10
            cut_dur = max(1, end - cur)
            sw_t    = min(1.0, max(0.0, (switch_f - 1 - cur) / cut_dur))
            sw_d    = d + (ed - d) * sw_t

            if switch_f - cur > MIN_CUT_SPAN:
                # 通常: 前カット終了フレームを書く
                _write(switch_f - 1, sw_d, rx, ry, rz, sdx, sdz, fov_ov, comp, py_off)
            else:
                # 短すぎるカット: 開始フレームを取り消す（終了フレームも書かない）
                # ※ cur-1（前カット終点）は削除しない: 削除すると前カット内の
                #   Y追従中間フレームが孤立し、異常に長い補間区間を作る原因になる
                seen.pop(cur, None)

            # 次カット開始フレーム（← ここが CUT点: 値が変わる）
            def_idx += 1
            ncd    = cut_defs[def_idx % len(cut_defs)]
            nd     = ncd["distance"]
            nrx, nry, nrz = ncd["rot_x"], ncd["rot_y"], ncd["rot_z"]
            nsdx, nsdz    = ncd.get("screen_dx", 0.0), ncd.get("screen_dz", 0.0)
            nfov_ov        = ncd.get("fov_override", None)
            ncomp          = ncd.get("composition", "head")
            n_py_off       = ncd.get("pos_y_offset", 0.0)
            _write_cut_start(switch_f, nd, nrx, nry, nrz, nsdx, nsdz, nfov_ov, ncomp, n_py_off)

            cur        = switch_f
            skip_start = True
        else:
            # ── Y追従スキャン（超クロースアップ限定）──
            #
            # 広角カットでは中間フレームがカクカクの原因になるため無効。
            # avg_d ≤ 22 のクロースアップのみ。引きカットは中間フレームなし。
            #
            # パターンB: 最低点から立ち上がり（座り→立ち等）
            # パターンC: ジャンプ追従（アップ時にモデルが飛び出るのを防ぐ）
            # ※ パターンA（急落）・D（前傾変化）は中間フレームのジャーク原因のため削除
            #
            MY_THRESH   = 3.5    # センターY 変化閾値（大きめにして感度を下げる）
            JUMP_THRESH = 2.5    # ジャンプ追従閾値
            MY_SPAN     = 6      # スキャン間隔（フレーム）
            END_MARGIN  = 20     # 終点前 N フレームはスキャンしない

            avg_d = (abs(d) + abs(ed)) / 2.0

            if avg_d <= 22.0 and end - cur > MY_SPAN * 2:
                cut_len  = max(1, end - cur)
                scan_end = max(cur + MY_SPAN, end - END_MARGIN)

                start_my = get_model_pos(bones, cur)[1]
                prev_my  = start_my
                min_my   = start_my
                min_f    = cur

                for sf in range(cur + MY_SPAN, scan_end, MY_SPAN):
                    curr_my = get_model_pos(bones, sf)[1]
                    t_sf    = min(1.0, max(0.0, (sf - cur) / cut_len))
                    d_sf    = d + (ed - d) * t_sf
                    # rot_y / rot_x を時刻 t_sf で線形補間（ドリフトモード対応）
                    ry_sf   = ry + (end_ry - ry) * t_sf
                    rx_sf   = rx + (end_rx - rx) * t_sf

                    # 最低点更新
                    if curr_my < min_my:
                        min_my = curr_my; min_f = sf

                    # パターンB: 最低点から立ち上がり
                    if curr_my - min_my > MY_THRESH:
                        t_min  = min(1.0, max(0.0, (min_f - cur) / cut_len))
                        ry_min = ry + (end_ry - ry) * t_min
                        rx_min = rx + (end_rx - rx) * t_min
                        _write_y_locked(min_f, d + (ed - d) * t_min,
                                        rx_min, ry_min, rz, sdx, sdz, fov_ov, py_off)
                        _write_y_locked(sf, d_sf, rx_sf, ry_sf, rz, sdx, sdz, fov_ov, py_off)
                        min_my = curr_my; min_f = sf

                    # パターンC: ジャンプ追従（アップ時のみ: モデルが上にはみ出るのを防ぐ）
                    elif curr_my - prev_my > JUMP_THRESH:
                        _write_y_locked(sf, d_sf, rx, ry, rz, sdx, sdz, fov_ov, py_off)

                    prev_my = curr_my

            # 次カット先読み: 同dist/fov なら終了・開始フレームを両方省略
            # → 孤立◆をなくし 始点→次次終点 を滑らかに一本化
            ncd_nxt  = cut_defs[(def_idx + 1) % len(cut_defs)]
            nfov_nxt = (ncd_nxt.get("fov_override")
                        or dist_to_fov(abs(ncd_nxt["distance"]), fov_base))
            cur_efov = fov_ov or dist_to_fov(abs(ed), fov_base)
            same_next = (nfov_nxt == cur_efov
                         and round(abs(ncd_nxt["distance"])) == round(abs(ed)))

            # 通常終了フレーム（次が同パラメータなら省略して滑らかに繋ぐ）
            if not same_next:
                _write(end, ed, end_rx, end_ry, rz, sdx, sdz, fov_ov, comp, py_off, s_curve)
            cur     = end + 1
            def_idx += 1
            if same_next:
                skip_start = True

    # 最終フレーム保証 + 正面向き強制（final_rot_y=0.0 で正面に向ける）
    # 直前の◆が END_GAP フレーム以内にある場合は追加しない（◆◆◆の連続防止）
    END_GAP = 50  # 通常カット1本分(≈40F)より広くして孤立◆を防ぐ
    last_f  = max(seen.keys()) if seen else 0
    if total_frames not in seen:
        if seen and total_frames - last_f <= END_GAP:
            # 直前◆が近すぎる → 追加せず、直前◆の rot_y だけ正面に向ける
            seen[last_f]["rot_y"] = final_rot_y
        else:
            seen[total_frames] = build_frame(
                total_frames, bones, char_h, d, rx, final_rot_y, rz, fov_base, sdx, sdz)
    else:
        seen[total_frames]["rot_y"] = final_rot_y

    # 末尾 ◆◆ → ◆ 整理 (ループ):
    # 最終◆の直前 TAIL_CLEAN フレーム以内にある余分な◆を全て削除する
    # Y追従中間点が複数残るケースでも確実に1つだけになる
    TAIL_CLEAN = 25
    final_f = max(seen.keys())
    for k in sorted(seen.keys()):
        if k != final_f and final_f - k <= TAIL_CLEAN:
            del seen[k]

    return [seen[k] for k in sorted(seen.keys())]


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# app.py デバッグプレビュー用
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
def get_target(bones: dict, frame: int,
               char_h: float, distance: float,
               rot_x: float) -> dict:
    action = _classify(bones, frame, char_h)
    safety = get_safety(bones, frame, char_h)
    banzai = _banzai_pull(bones, frame, char_h)
    dist   = _safe_dist(distance, action, safety["pull"], banzai)
    fov    = dist_to_fov(dist, 30)
    pos_y  = _pos_y(frame, bones, char_h, dist, fov)
    mx, _, mz = get_model_pos(bones, frame)
    return {
        "frame": frame, "distance": dist,
        "pos_x": mx, "pos_y": pos_y, "pos_z": mz,
        "rot_x": rot_x, "rot_y": 0.0, "rot_z": 0.0,
        "fov": fov,
        "action": action, "safety": safety,
    }
