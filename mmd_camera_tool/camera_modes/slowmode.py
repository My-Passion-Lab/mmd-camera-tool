# slowmode.py  -- ゆっくりモード (anime telephoto style)
#
# FOV=12 固定（望遠・アニメ風圧縮効果）
# 距離 -80 ~ -150 (FOV12でフル体が収まる範囲)
# カット長 60~100F でゆったり流れる
# S字補間でなめらかに
#
# チェーン構造:
#   ◆◆ [始端] --> NF --> ◆ [中継点] --> NF --> ◆◆ [終端]
#   中継点の force_start=True で単独◆を強制書き込み

import random
from vmd_reader import get_total_frames
from camera_core import generate_cuts

FOV = 12   # 全カット共通の視野角


def generate(char_height_mmd: float, bones: dict, fov_base: int = 30) -> list:

    chains = []

    # =========================================================
    # (1) ゆるやかなズームイン（引き → 寄り）
    # =========================================================

    # 正面 フル体 → 上半身
    chains.append([
        {"distance": -140.0, "end_distance": -110.0,
         "rot_y": 0.0, "rot_x": 0.0, "rot_z": 0.0,
         "length": 90, "s_curve": True, "composition": "body",
         "fov_override": FOV},
        {"distance": -110.0, "end_distance": -85.0,
         "rot_y": 0.0, "rot_x": 0.02, "rot_z": 0.0,
         "length": 90, "s_curve": True, "composition": "body",
         "fov_override": FOV, "force_start": True},
    ])

    # 斜め右 フル体 → 中間
    chains.append([
        {"distance": -135.0, "end_distance": -110.0,
         "rot_y": 0.20, "rot_x": 0.0, "rot_z": 0.0,
         "length": 80, "s_curve": True, "composition": "body",
         "fov_override": FOV},
        {"distance": -110.0, "end_distance": -88.0,
         "rot_y": 0.20, "rot_x": 0.02, "rot_z": 0.0,
         "length": 80, "s_curve": True, "composition": "body",
         "fov_override": FOV, "force_start": True},
    ])

    # 斜め左 フル体 → 中間
    chains.append([
        {"distance": -135.0, "end_distance": -108.0,
         "rot_y": -0.20, "rot_x": 0.0, "rot_z": 0.0,
         "length": 80, "s_curve": True, "composition": "body",
         "fov_override": FOV},
        {"distance": -108.0, "end_distance": -85.0,
         "rot_y": -0.20, "rot_x": 0.02, "rot_z": 0.0,
         "length": 80, "s_curve": True, "composition": "body",
         "fov_override": FOV, "force_start": True},
    ])

    # =========================================================
    # (2) ゆるやかなズームアウト（寄り → 引き）
    # =========================================================

    # 正面 上半身 → フル体
    chains.append([
        {"distance": -85.0, "end_distance": -110.0,
         "rot_y": 0.0, "rot_x": 0.02, "rot_z": 0.0,
         "length": 85, "s_curve": True, "composition": "body",
         "fov_override": FOV},
        {"distance": -110.0, "end_distance": -138.0,
         "rot_y": 0.0, "rot_x": 0.0, "rot_z": 0.0,
         "length": 85, "s_curve": True, "composition": "body",
         "fov_override": FOV, "force_start": True},
    ])

    # 斜め右 中間 → 引き
    chains.append([
        {"distance": -90.0, "end_distance": -115.0,
         "rot_y": 0.18, "rot_x": 0.02, "rot_z": 0.0,
         "length": 75, "s_curve": True, "composition": "body",
         "fov_override": FOV},
        {"distance": -115.0, "end_distance": -140.0,
         "rot_y": 0.18, "rot_x": 0.0, "rot_z": 0.0,
         "length": 75, "s_curve": True, "composition": "body",
         "fov_override": FOV, "force_start": True},
    ])

    # =========================================================
    # (3) 横流し（パン）
    # =========================================================

    # 右から正面へ → 正面から左へ
    chains.append([
        {"distance": -120.0, "end_distance": -112.0,
         "rot_y": -0.22, "end_rot_y": 0.0,
         "rot_x": 0.0, "rot_z": 0.0,
         "length": 80, "s_curve": True, "composition": "body",
         "fov_override": FOV},
        {"distance": -112.0, "end_distance": -120.0,
         "rot_y": 0.0, "end_rot_y": 0.22,
         "rot_x": 0.0, "rot_z": 0.0,
         "length": 80, "s_curve": True, "composition": "body",
         "fov_override": FOV, "force_start": True},
    ])

    # 左から正面へ → 正面から右へ
    chains.append([
        {"distance": -120.0, "end_distance": -112.0,
         "rot_y": 0.22, "end_rot_y": 0.0,
         "rot_x": 0.0, "rot_z": 0.0,
         "length": 80, "s_curve": True, "composition": "body",
         "fov_override": FOV},
        {"distance": -112.0, "end_distance": -120.0,
         "rot_y": 0.0, "end_rot_y": -0.22,
         "rot_x": 0.0, "rot_z": 0.0,
         "length": 80, "s_curve": True, "composition": "body",
         "fov_override": FOV, "force_start": True},
    ])

    # =========================================================
    # (4) ゆっくり回り込み
    # =========================================================

    # 正面 → 右斜め（ゆっくり周回）
    chains.append([
        {"distance": -125.0, "end_distance": -118.0,
         "rot_y": 0.0, "end_rot_y": 0.20,
         "rot_x": 0.0, "rot_z": 0.0,
         "length": 90, "s_curve": True, "composition": "body",
         "fov_override": FOV},
        {"distance": -118.0, "end_distance": -112.0,
         "rot_y": 0.20, "end_rot_y": 0.40,
         "rot_x": 0.0, "rot_z": 0.0,
         "length": 90, "s_curve": True, "composition": "body",
         "fov_override": FOV, "force_start": True},
    ])

    # 正面 → 左斜め
    chains.append([
        {"distance": -125.0, "end_distance": -118.0,
         "rot_y": 0.0, "end_rot_y": -0.20,
         "rot_x": 0.0, "rot_z": 0.0,
         "length": 90, "s_curve": True, "composition": "body",
         "fov_override": FOV},
        {"distance": -118.0, "end_distance": -112.0,
         "rot_y": -0.20, "end_rot_y": -0.40,
         "rot_x": 0.0, "rot_z": 0.0,
         "length": 90, "s_curve": True, "composition": "body",
         "fov_override": FOV, "force_start": True},
    ])

    # =========================================================
    # (5) 俯瞰ハイアングル
    # =========================================================

    # 正面 ハイアングル → ズームイン
    chains.append([
        {"distance": -145.0, "end_distance": -120.0,
         "rot_y": 0.0, "rot_x": -0.12, "rot_z": 0.0,
         "length": 85, "s_curve": True, "composition": "body",
         "fov_override": FOV},
        {"distance": -120.0, "end_distance": -95.0,
         "rot_y": 0.0, "rot_x": -0.08, "rot_z": 0.0,
         "length": 85, "s_curve": True, "composition": "body",
         "fov_override": FOV, "force_start": True},
    ])

    # 斜め ハイアングル 流し
    chains.append([
        {"distance": -130.0, "end_distance": -118.0,
         "rot_y": 0.15, "end_rot_y": 0.0,
         "rot_x": -0.10, "rot_z": 0.0,
         "length": 80, "s_curve": True, "composition": "body",
         "fov_override": FOV},
        {"distance": -118.0, "end_distance": -130.0,
         "rot_y": 0.0, "end_rot_y": -0.15,
         "rot_x": -0.08, "rot_z": 0.0,
         "length": 80, "s_curve": True, "composition": "body",
         "fov_override": FOV, "force_start": True},
    ])

    # =========================================================
    # (6) 後ろアングル
    # =========================================================

    # 後ろ正面 引き → 中間
    chains.append([
        {"distance": -130.0, "end_distance": -110.0,
         "rot_y": 3.14, "rot_x": 0.0, "rot_z": 0.0,
         "length": 85, "s_curve": True, "composition": "body",
         "fov_override": FOV},
        {"distance": -110.0, "end_distance": -90.0,
         "rot_y": 3.14, "rot_x": 0.02, "rot_z": 0.0,
         "length": 85, "s_curve": True, "composition": "body",
         "fov_override": FOV, "force_start": True},
    ])

    # =========================================================
    # チェーンをシャッフルして cut_defs に展開
    # =========================================================
    random.shuffle(chains)

    cut_defs = []
    for chain in chains:
        for cd in chain:
            c = dict(cd)
            c.setdefault("end_distance", c["distance"])
            c.setdefault("end_rot_y",    c["rot_y"])
            c.setdefault("end_rot_x",    c.get("rot_x", 0.0))
            c.setdefault("screen_dx",    0.0)
            c.setdefault("screen_dz",    0.0)
            cut_defs.append(c)

    total = get_total_frames(bones) if bones else 300

    # イントロカット: 曲冒頭の静止期間に正面フル体で待機
    intro = {
        "distance":     -130.0,
        "end_distance": -120.0,
        "rot_x": 0.0, "rot_y": 0.0, "rot_z": 0.0,
        "composition": "body",
        "fov_override": FOV,
    }

    return generate_cuts(bones, char_height_mmd, fov_base, cut_defs, total,
                         intro_cut=intro)
