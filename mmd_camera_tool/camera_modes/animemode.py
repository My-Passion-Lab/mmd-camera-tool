# animemode.py  -- アニメモード (anime-style camera)
#
# アニメカメラの基本ルール:
#   1. 1カットにつき動きは1種類だけ（パン・ズームイン・ズームアウト・静止）
#   2. カット間は ◆◆ でハードカット（チェーン構造なし）
#   3. FOV=12 望遠固定（アニメ的な圧縮感）
#   4. S字補間でショット内は滑らか
#
# 動きのタイプ:
#   static   : ほぼ静止（わずかにゆっくり寄る）
#   zoom_in  : ゆっくりズームイン（引き → 寄り）
#   zoom_out : ゆっくりズームアウト（寄り → 引き）
#   pan      : 水平パン（角度が変わる）
#   orbit    : ゆっくり回り込み（距離 + 角度が同時に変わる）

import random
from vmd_reader import get_total_frames
from camera_core import generate_cuts

FOV = 12   # 全カット共通の視野角


def generate(char_height_mmd: float, bones: dict, fov_base: int = 30) -> list:

    # チェーンなし = 単独カットのリスト
    cut_pool = []

    # =========================================================
    # [A] 静止 ― ほぼ動かない・わずかにゆっくり寄る
    # =========================================================

    # 正面 静止（極わずかズームイン）
    cut_pool.append(
        {"distance": -128.0, "end_distance": -120.0,
         "rot_y": 0.0, "rot_x": 0.0, "rot_z": 0.0,
         "length": 80, "s_curve": True, "composition": "body",
         "fov_override": FOV})

    # 斜め右 静止
    cut_pool.append(
        {"distance": -125.0, "end_distance": -118.0,
         "rot_y": 0.18, "rot_x": 0.0, "rot_z": 0.0,
         "length": 75, "s_curve": True, "composition": "body",
         "fov_override": FOV})

    # 斜め左 静止
    cut_pool.append(
        {"distance": -125.0, "end_distance": -118.0,
         "rot_y": -0.18, "rot_x": 0.0, "rot_z": 0.0,
         "length": 75, "s_curve": True, "composition": "body",
         "fov_override": FOV})

    # 後ろ 静止
    cut_pool.append(
        {"distance": -122.0, "end_distance": -115.0,
         "rot_y": 3.14, "rot_x": 0.0, "rot_z": 0.0,
         "length": 80, "s_curve": True, "composition": "body",
         "fov_override": FOV})

    # 俯瞰 静止
    cut_pool.append(
        {"distance": -130.0, "end_distance": -122.0,
         "rot_y": 0.0, "rot_x": -0.12, "rot_z": 0.0,
         "length": 75, "s_curve": True, "composition": "body",
         "fov_override": FOV})

    # =========================================================
    # [B] ズームイン ― 引き → 寄り
    # =========================================================

    # 正面 ズームイン
    cut_pool.append(
        {"distance": -148.0, "end_distance": -105.0,
         "rot_y": 0.0, "rot_x": 0.0, "rot_z": 0.0,
         "length": 90, "s_curve": True, "composition": "body",
         "fov_override": FOV})

    # 斜め右 ズームイン
    cut_pool.append(
        {"distance": -145.0, "end_distance": -100.0,
         "rot_y": 0.20, "rot_x": 0.0, "rot_z": 0.0,
         "length": 85, "s_curve": True, "composition": "body",
         "fov_override": FOV})

    # 斜め左 ズームイン
    cut_pool.append(
        {"distance": -145.0, "end_distance": -100.0,
         "rot_y": -0.20, "rot_x": 0.0, "rot_z": 0.0,
         "length": 85, "s_curve": True, "composition": "body",
         "fov_override": FOV})

    # 俯瞰 ズームイン
    cut_pool.append(
        {"distance": -150.0, "end_distance": -110.0,
         "rot_y": 0.0, "rot_x": -0.14, "rot_z": 0.0,
         "length": 90, "s_curve": True, "composition": "body",
         "fov_override": FOV})

    # 後ろ ズームイン
    cut_pool.append(
        {"distance": -140.0, "end_distance": -100.0,
         "rot_y": 3.14, "rot_x": 0.0, "rot_z": 0.0,
         "length": 85, "s_curve": True, "composition": "body",
         "fov_override": FOV})

    # =========================================================
    # [C] ズームアウト ― 寄り → 引き
    # =========================================================

    # 正面 ズームアウト
    cut_pool.append(
        {"distance": -95.0, "end_distance": -145.0,
         "rot_y": 0.0, "rot_x": 0.0, "rot_z": 0.0,
         "length": 90, "s_curve": True, "composition": "body",
         "fov_override": FOV})

    # 斜め右 ズームアウト
    cut_pool.append(
        {"distance": -100.0, "end_distance": -148.0,
         "rot_y": 0.20, "rot_x": 0.0, "rot_z": 0.0,
         "length": 85, "s_curve": True, "composition": "body",
         "fov_override": FOV})

    # 斜め左 ズームアウト
    cut_pool.append(
        {"distance": -100.0, "end_distance": -148.0,
         "rot_y": -0.20, "rot_x": 0.0, "rot_z": 0.0,
         "length": 85, "s_curve": True, "composition": "body",
         "fov_override": FOV})

    # =========================================================
    # [D] 水平パン ― 右→左 または 左→右
    # =========================================================

    # 右から正面へパン（rot_y 減る）
    cut_pool.append(
        {"distance": -122.0, "end_distance": -122.0,
         "rot_y": 0.30, "end_rot_y": 0.0,
         "rot_x": 0.0, "rot_z": 0.0,
         "length": 85, "s_curve": True, "composition": "body",
         "fov_override": FOV})

    # 左から正面へパン
    cut_pool.append(
        {"distance": -122.0, "end_distance": -122.0,
         "rot_y": -0.30, "end_rot_y": 0.0,
         "rot_x": 0.0, "rot_z": 0.0,
         "length": 85, "s_curve": True, "composition": "body",
         "fov_override": FOV})

    # 正面から右へパン
    cut_pool.append(
        {"distance": -120.0, "end_distance": -120.0,
         "rot_y": 0.0, "end_rot_y": 0.28,
         "rot_x": 0.0, "rot_z": 0.0,
         "length": 80, "s_curve": True, "composition": "body",
         "fov_override": FOV})

    # 正面から左へパン
    cut_pool.append(
        {"distance": -120.0, "end_distance": -120.0,
         "rot_y": 0.0, "end_rot_y": -0.28,
         "rot_x": 0.0, "rot_z": 0.0,
         "length": 80, "s_curve": True, "composition": "body",
         "fov_override": FOV})

    # 右から左へパン（通過）
    cut_pool.append(
        {"distance": -118.0, "end_distance": -118.0,
         "rot_y": 0.25, "end_rot_y": -0.25,
         "rot_x": 0.0, "rot_z": 0.0,
         "length": 90, "s_curve": True, "composition": "body",
         "fov_override": FOV})

    # 左から右へパン（通過）
    cut_pool.append(
        {"distance": -118.0, "end_distance": -118.0,
         "rot_y": -0.25, "end_rot_y": 0.25,
         "rot_x": 0.0, "rot_z": 0.0,
         "length": 90, "s_curve": True, "composition": "body",
         "fov_override": FOV})

    # =========================================================
    # [E] 回り込み ― 角度 + 距離が同時に変わる
    # =========================================================

    # 右 → 正面（角度 + わずかズームイン）
    cut_pool.append(
        {"distance": -135.0, "end_distance": -118.0,
         "rot_y": 0.38, "end_rot_y": 0.0,
         "rot_x": 0.0, "rot_z": 0.0,
         "length": 90, "s_curve": True, "composition": "body",
         "fov_override": FOV})

    # 左 → 正面（角度 + わずかズームイン）
    cut_pool.append(
        {"distance": -135.0, "end_distance": -118.0,
         "rot_y": -0.38, "end_rot_y": 0.0,
         "rot_x": 0.0, "rot_z": 0.0,
         "length": 90, "s_curve": True, "composition": "body",
         "fov_override": FOV})

    # 正面 → 右（角度 + わずかズームアウト）
    cut_pool.append(
        {"distance": -115.0, "end_distance": -132.0,
         "rot_y": 0.0, "end_rot_y": 0.35,
         "rot_x": 0.0, "rot_z": 0.0,
         "length": 90, "s_curve": True, "composition": "body",
         "fov_override": FOV})

    # 正面 → 左
    cut_pool.append(
        {"distance": -115.0, "end_distance": -132.0,
         "rot_y": 0.0, "end_rot_y": -0.35,
         "rot_x": 0.0, "rot_z": 0.0,
         "length": 90, "s_curve": True, "composition": "body",
         "fov_override": FOV})

    # =========================================================
    # シャッフルして cut_defs に展開（チェーンなし）
    # =========================================================
    random.shuffle(cut_pool)

    cut_defs = []
    for cd in cut_pool:
        c = dict(cd)
        c.setdefault("end_distance", c["distance"])
        c.setdefault("end_rot_y",    c["rot_y"])
        c.setdefault("end_rot_x",    c.get("rot_x", 0.0))
        c.setdefault("screen_dx",    0.0)
        c.setdefault("screen_dz",    0.0)
        cut_defs.append(c)

    total = get_total_frames(bones) if bones else 300

    # イントロカット: 曲冒頭の静止期間に正面ほぼ静止で待機
    intro = {
        "distance":     -130.0,
        "end_distance": -125.0,
        "rot_x": 0.0, "rot_y": 0.0, "rot_z": 0.0,
        "composition": "body",
        "fov_override": FOV,
    }

    return generate_cuts(bones, char_height_mmd, fov_base, cut_defs, total,
                         intro_cut=intro)
