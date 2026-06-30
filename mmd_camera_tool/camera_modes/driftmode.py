# driftmode.py  -- Drift mode camera (chained cut version)
#
# チェーン構造:
#   ◆◆ [始端] --> NF --> ◆ [中継点 force_start] --> NF --> ◆◆ [終端]
#
# force_start=True のカットは same_next スキップ後も単独 ◆ を書き込む
# -> 中継点が MMD で見えて、値を手動編集できる
#
# カット長の目安:
#   短め 25~30F / 中間 35~40F / 長め 45~50F

import random
from vmd_reader import get_total_frames
from camera_core import generate_cuts


def generate(char_height_mmd: float, bones: dict, fov_base: int = 30) -> list:

    chains = []

    # =====================================================================
    # (1) ズームイン系チェーン（遠→近、2～3段階）
    # =====================================================================

    # 引き → 中間 → 引き気味（正面、2ステップ）
    chains.append([
        {"distance": -58.0, "end_distance": -48.0,
         "rot_y": 0.0, "end_rot_y": 0.0,
         "rot_x": 0.0, "rot_z": 0.0,
         "length": 40, "s_curve": True, "composition": "body"},
        {"distance": -48.0, "end_distance": -38.0,
         "rot_y": 0.0, "end_rot_y": 0.0,
         "rot_x": 0.0, "rot_z": 0.0,
         "length": 40, "s_curve": True, "composition": "body",
         "force_start": True},
    ])

    # 引き → 中間アップ → やや寄り（斜め、2ステップ）
    chains.append([
        {"distance": -55.0, "end_distance": -44.0,
         "rot_y": 0.20, "end_rot_y": 0.20,
         "rot_x": 0.03, "rot_z": 0.0,
         "length": 38, "s_curve": True, "composition": "body"},
        {"distance": -44.0, "end_distance": -33.0,
         "rot_y": 0.20, "end_rot_y": 0.20,
         "rot_x": 0.05, "rot_z": 0.0,
         "length": 38, "s_curve": True, "composition": "body",
         "force_start": True},
    ])

    # 3段ズームイン（引き → 中 → アップ）
    chains.append([
        {"distance": -60.0, "end_distance": -50.0,
         "rot_y": 0.0, "end_rot_y": 0.0,
         "rot_x": 0.0, "rot_z": 0.0,
         "length": 30, "s_curve": True, "composition": "body"},
        {"distance": -50.0, "end_distance": -40.0,
         "rot_y": 0.0, "end_rot_y": 0.0,
         "rot_x": 0.02, "rot_z": 0.0,
         "length": 30, "s_curve": True, "composition": "body",
         "force_start": True},
        {"distance": -40.0, "end_distance": -28.0,
         "rot_y": 0.0, "end_rot_y": 0.0,
         "rot_x": 0.04, "rot_z": 0.0,
         "length": 30, "s_curve": True, "composition": "head",
         "force_start": True},
    ])

    # =====================================================================
    # (2) ズームアウト系チェーン（近→遠）
    # =====================================================================

    # アップ → 中間 → 引き（正面）
    chains.append([
        {"distance": -32.0, "end_distance": -42.0,
         "rot_y": 0.0, "end_rot_y": 0.0,
         "rot_x": 0.04, "rot_z": 0.0,
         "length": 38, "s_curve": True, "composition": "head"},
        {"distance": -42.0, "end_distance": -54.0,
         "rot_y": 0.0, "end_rot_y": 0.0,
         "rot_x": 0.02, "rot_z": 0.0,
         "length": 38, "s_curve": True, "composition": "body",
         "force_start": True},
    ])

    # 中間 → 広角（斜め）
    chains.append([
        {"distance": -38.0, "end_distance": -48.0,
         "rot_y": -0.18, "end_rot_y": -0.18,
         "rot_x": 0.03, "rot_z": 0.0,
         "length": 40, "s_curve": True, "composition": "body"},
        {"distance": -48.0, "end_distance": -58.0,
         "rot_y": -0.18, "end_rot_y": -0.18,
         "rot_x": 0.01, "rot_z": 0.0,
         "length": 40, "s_curve": True, "composition": "body",
         "force_start": True},
    ])

    # =====================================================================
    # (3) 横流し系チェーン（左右パン）
    # =====================================================================

    # 正面→右 流し（中継点で少し寄る）
    chains.append([
        {"distance": -54.0, "end_distance": -48.0,
         "rot_y": -0.18, "end_rot_y": 0.0,
         "rot_x": 0.0, "rot_z": 0.0,
         "length": 40, "s_curve": True, "composition": "body"},
        {"distance": -48.0, "end_distance": -52.0,
         "rot_y": 0.0, "end_rot_y": 0.18,
         "rot_x": 0.0, "rot_z": 0.0,
         "length": 40, "s_curve": True, "composition": "body",
         "force_start": True},
    ])

    # 正面→左 流し
    chains.append([
        {"distance": -54.0, "end_distance": -48.0,
         "rot_y": 0.18, "end_rot_y": 0.0,
         "rot_x": 0.0, "rot_z": 0.0,
         "length": 40, "s_curve": True, "composition": "body"},
        {"distance": -48.0, "end_distance": -52.0,
         "rot_y": 0.0, "end_rot_y": -0.18,
         "rot_x": 0.0, "rot_z": 0.0,
         "length": 40, "s_curve": True, "composition": "body",
         "force_start": True},
    ])

    # 顔アップ 左右流し
    chains.append([
        {"distance": -30.0, "end_distance": -26.0,
         "rot_y": -0.15, "end_rot_y": 0.0,
         "rot_x": 0.05, "rot_z": 0.0,
         "length": 35, "s_curve": True, "composition": "head"},
        {"distance": -26.0, "end_distance": -30.0,
         "rot_y": 0.0, "end_rot_y": 0.15,
         "rot_x": 0.05, "rot_z": 0.0,
         "length": 35, "s_curve": True, "composition": "head",
         "force_start": True},
    ])

    # 後ろアングル 流し
    chains.append([
        {"distance": -50.0, "end_distance": -48.0,
         "rot_y": 2.8, "end_rot_y": 2.6,
         "rot_x": 0.02, "rot_z": 0.0,
         "length": 40, "s_curve": True, "composition": "body"},
        {"distance": -48.0, "end_distance": -50.0,
         "rot_y": 2.6, "end_rot_y": 2.4,
         "rot_x": 0.02, "rot_z": 0.0,
         "length": 40, "s_curve": True, "composition": "body",
         "force_start": True},
    ])

    # =====================================================================
    # (4) 回り込み系チェーン（正面→斜め→横）
    # =====================================================================

    # 正面→右斜め 回り込み（2段）
    chains.append([
        {"distance": -52.0, "end_distance": -50.0,
         "rot_y": 0.0, "end_rot_y": 0.25,
         "rot_x": 0.0, "rot_z": 0.0,
         "length": 40, "s_curve": True, "composition": "body"},
        {"distance": -50.0, "end_distance": -48.0,
         "rot_y": 0.25, "end_rot_y": 0.50,
         "rot_x": 0.0, "rot_z": 0.0,
         "length": 40, "s_curve": True, "composition": "body",
         "force_start": True},
    ])

    # 正面→左斜め 回り込み（2段）
    chains.append([
        {"distance": -52.0, "end_distance": -50.0,
         "rot_y": 0.0, "end_rot_y": -0.25,
         "rot_x": 0.0, "rot_z": 0.0,
         "length": 40, "s_curve": True, "composition": "body"},
        {"distance": -50.0, "end_distance": -48.0,
         "rot_y": -0.25, "end_rot_y": -0.50,
         "rot_x": 0.0, "rot_z": 0.0,
         "length": 40, "s_curve": True, "composition": "body",
         "force_start": True},
    ])

    # 俯瞰 回り込み（3段）
    chains.append([
        {"distance": -56.0, "end_distance": -53.0,
         "rot_y": 0.0, "end_rot_y": 0.15,
         "rot_x": 0.10, "rot_z": 0.0,
         "length": 30, "s_curve": True, "composition": "body"},
        {"distance": -53.0, "end_distance": -50.0,
         "rot_y": 0.15, "end_rot_y": 0.30,
         "rot_x": 0.12, "rot_z": 0.0,
         "length": 30, "s_curve": True, "composition": "body",
         "force_start": True},
        {"distance": -50.0, "end_distance": -47.0,
         "rot_y": 0.30, "end_rot_y": 0.45,
         "rot_x": 0.14, "rot_z": 0.0,
         "length": 30, "s_curve": True, "composition": "body",
         "force_start": True},
    ])

    # =====================================================================
    # (5) 複合系チェーン（ズーム＋パン）
    # =====================================================================

    # ズームインしながら右回り
    chains.append([
        {"distance": -56.0, "end_distance": -47.0,
         "rot_y": -0.10, "end_rot_y": 0.0,
         "rot_x": 0.0, "rot_z": 0.0,
         "length": 38, "s_curve": True, "composition": "body"},
        {"distance": -47.0, "end_distance": -38.0,
         "rot_y": 0.0, "end_rot_y": 0.10,
         "rot_x": 0.02, "rot_z": 0.0,
         "length": 38, "s_curve": True, "composition": "body",
         "force_start": True},
    ])

    # ズームアウトしながら左流し
    chains.append([
        {"distance": -36.0, "end_distance": -46.0,
         "rot_y": 0.10, "end_rot_y": 0.0,
         "rot_x": 0.02, "rot_z": 0.0,
         "length": 38, "s_curve": True, "composition": "body"},
        {"distance": -46.0, "end_distance": -56.0,
         "rot_y": 0.0, "end_rot_y": -0.10,
         "rot_x": 0.0, "rot_z": 0.0,
         "length": 38, "s_curve": True, "composition": "body",
         "force_start": True},
    ])

    # =====================================================================
    # チェーンをシャッフルして cut_defs に展開
    # =====================================================================
    random.shuffle(chains)

    cut_defs = []
    for chain in chains:
        for cd in chain:
            c = dict(cd)
            c.setdefault("end_distance", c["distance"])
            c.setdefault("end_rot_y", c["rot_y"])
            c.setdefault("end_rot_x", c.get("rot_x", 0.0))
            c.setdefault("screen_dx", 0.0)
            c.setdefault("screen_dz", 0.0)
            cut_defs.append(c)

    total = get_total_frames(bones) if bones else 300

    # Intro cut: 曲冒頭の静止期間に正面引きで待機
    intro = {
        "distance": -54.0,
        "end_distance": -50.0,
        "rot_x": 0.0, "rot_y": 0.0, "rot_z": 0.0,
        "composition": "body",
    }

    return generate_cuts(bones, char_height_mmd, fov_base, cut_defs, total,
                         intro_cut=intro)
