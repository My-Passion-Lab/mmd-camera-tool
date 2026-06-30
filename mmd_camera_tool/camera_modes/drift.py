# camera_modes/drift.py
from vmd_reader import get_total_frames
from camera_core import generate_cuts


def generate(char_height_mmd: float, bones: dict,
             fov_base: int = 30) -> list:

    total = get_total_frames(bones) if bones else 300

    # ── カット定義 ──
    # rot_x: 負=見下ろし(ハイ), 正=見上げ(ロー)
    # rot_y: 0=正面, ±0.38=斜め, ±1.57=真横, ±2.36=斜め後ろ, ±2.80=ほぼ後ろ, ±3.14=真後ろ
    # fov_override: 視野角強制指定（省略で距離連動）
    # composition: "head"=頭追い(default) / "body"=全身 / "foot"=足元
    # pos_y_offset: カメラ中心Yの追加オフセット（foot構図微調整用）
    #
    # 自分で調整するには:
    #   "length"       → フレーム数（短くすると切り替えが速くなる）
    #   "distance"     → カット開始時のカメラ距離（負値）
    #   "end_distance" → カット終了時のカメラ距離（省略で固定）
    #
    cut_defs = [

        # ═══════════════════════════════════════════
        # パターン A (7カット / 300F) 正面メイン
        # ═══════════════════════════════════════════
        {"length": 24, "distance": -16.0, "end_distance": -19.0,
         "rot_x": -0.05, "rot_y":  0.00, "rot_z":  0.000},
        {"length": 56, "distance": -40.0, "end_distance": -55.0,
         "rot_x": -0.04, "rot_y":  0.00, "rot_z":  0.000},
        {"length": 20, "distance": -18.0, "end_distance": -21.0,
         "rot_x": -0.06, "rot_y":  0.08, "rot_z":  0.000},
        {"length": 48, "distance": -34.0, "end_distance": -50.0,
         "rot_x": -0.05, "rot_y":  0.00, "rot_z":  0.000},
        {"length": 40, "distance": -22.0, "end_distance": -38.0,
         "rot_x": -0.05, "rot_y":  0.38, "rot_z": -0.050},
        {"length": 56, "distance": -65.0, "end_distance": -18.0,
         "rot_x": -0.06, "rot_y":  0.00, "rot_z":  0.000},
        {"length": 56, "distance": -20.0, "end_distance": -57.0,
         "rot_x": -0.04, "rot_y":  0.00, "rot_z":  0.000},

        # ═══════════════════════════════════════════
        # パターン B (5カット / 212F) やや左 + 後ろズームイン
        # ═══════════════════════════════════════════
        {"length": 24, "distance": -16.0, "end_distance": -20.0,
         "rot_x": -0.07, "rot_y": -0.10, "rot_z":  0.000},
        {"length": 48, "distance": -42.0, "end_distance": -52.0,
         "rot_x": -0.05, "rot_y":  0.00, "rot_z":  0.000},
        {"length": 40, "distance": -20.0, "end_distance": -38.0,
         "rot_x": -0.05, "rot_y": -0.38, "rot_z":  0.050},
        {"length": 56, "distance": -20.0, "end_distance": -57.0,
         "rot_x": -0.04, "rot_y":  0.00, "rot_z":  0.000},
        {"length": 44, "distance": -66.0, "end_distance": -52.0,
         "fov_override": 30,
         "rot_x": -0.04, "rot_y":  3.14, "rot_z":  0.000},

        # ═══════════════════════════════════════════
        # パターン C (9カット / 360F) 斜め右・ローアングル混在
        # ═══════════════════════════════════════════
        {"length": 20, "distance": -18.0, "end_distance": -22.0,
         "rot_x": -0.18, "rot_y":  0.00, "rot_z":  0.000},
        {"length": 48, "distance": -38.0, "end_distance": -50.0,
         "rot_x": -0.05, "rot_y":  0.22, "rot_z": -0.060},
        {"length": 24, "distance": -14.0, "end_distance": -18.0,
         "rot_x": -0.05, "rot_y":  0.00, "rot_z":  0.000},
        {"length": 56, "distance": -38.0, "end_distance": -54.0,
         "rot_x": -0.09, "rot_y":  0.00, "rot_z":  0.000},
        {"length": 48, "distance": -28.0, "end_distance": -42.0,
         "rot_x":  0.22, "rot_y":  0.00, "rot_z":  0.000},
        {"length": 40, "distance": -28.0, "end_distance": -38.0,
         "rot_x": -0.05, "rot_y":  0.45, "rot_z": -0.040},
        {"length": 48, "distance": -20.0, "end_distance": -48.0,
         "rot_x": -0.05, "rot_y":  0.00, "rot_z":  0.000},
        {"length": 20, "distance": -18.0, "end_distance": -22.0,
         "rot_x": -0.06, "rot_y":  0.10, "rot_z":  0.000},
        {"length": 56, "distance": -36.0, "end_distance": -55.0,
         "rot_x": -0.04, "rot_y": -0.22, "rot_z":  0.000},

        # ═══════════════════════════════════════════
        # パターン D (4カット / 156F) 超クロース + 超広引き
        # ═══════════════════════════════════════════
        {"length": 24, "distance": -18.0, "end_distance": -20.0,
         "fov_override": 15,
         "rot_x": -0.05, "rot_y":  0.00, "rot_z":  0.000},
        {"length": 56, "distance": -90.0, "end_distance": -90.0,
         "fov_override": 30,
         "rot_x": -0.03, "rot_y":  0.00, "rot_z":  0.000},
        {"length": 20, "distance": -18.0, "end_distance": -22.0,
         "fov_override": 15,
         "rot_x": -0.06, "rot_y":  0.10, "rot_z":  0.000},
        {"length": 56, "distance": -90.0, "end_distance": -90.0,
         "fov_override": 30,
         "rot_x": -0.03, "rot_y":  0.22, "rot_z":  0.000},

        # ═══════════════════════════════════════════
        # パターン E (4カット / 156F) 締め: 全身 + 後ろ + 足元
        # ═══════════════════════════════════════════
        {"length": 48, "distance": -90.0, "end_distance": -82.0,
         "fov_override": 30,
         "rot_x": -0.04, "rot_y":  0.00, "rot_z":  0.000,
         "composition": "body"},
        {"length": 24, "distance": -86.0, "end_distance": -78.0,
         "fov_override": 30,
         "rot_x": -0.79, "rot_y":  3.14, "rot_z":  0.000},
        {"length": 56, "distance": -65.0, "end_distance": -55.0,
         "fov_override": 30,
         "rot_x": -0.05, "rot_y":  0.00, "rot_z":  0.000,
         "composition": "body"},
        {"length": 28, "distance": -18.0, "end_distance": -22.0,
         "fov_override": 60,
         "rot_x":  0.524, "rot_y":  0.00, "rot_z":  0.000,
         "composition": "foot", "pos_y_offset": 1.7},

        # ═══════════════════════════════════════════
        # パターン F (8カット / 340F) 後ろアングル拡張
        # 斜め後ろ右・左、後ろロー、後ろハイ など
        # ═══════════════════════════════════════════
        # F1 後ろ斜め右アップ（pos_y_offset+2.0: モデルが画面下寄りに）
        {"length": 24, "distance": -18.0, "end_distance": -24.0,
         "fov_override": 30,
         "rot_x": -0.06, "rot_y":  2.36, "rot_z":  0.000,
         "pos_y_offset": 2.0},
        # F2 後ろ斜め右引き
        {"length": 56, "distance": -42.0, "end_distance": -60.0,
         "fov_override": 30,
         "rot_x": -0.04, "rot_y":  2.36, "rot_z":  0.000},
        # F3 後ろ斜め左アップ（pos_y_offset+2.0）
        {"length": 20, "distance": -18.0, "end_distance": -22.0,
         "fov_override": 30,
         "rot_x": -0.06, "rot_y": -2.36, "rot_z":  0.000,
         "pos_y_offset": 2.0},
        # F4 後ろ斜め左引き
        {"length": 56, "distance": -44.0, "end_distance": -62.0,
         "fov_override": 30,
         "rot_x": -0.04, "rot_y": -2.36, "rot_z":  0.000},
        # F5 後ろローアングル（下から見上げ）
        {"length": 40, "distance": -28.0, "end_distance": -38.0,
         "fov_override": 30,
         "rot_x":  0.18, "rot_y":  3.14, "rot_z":  0.000},
        # F6 後ろズームイン（遠→近）
        {"length": 56, "distance": -70.0, "end_distance": -50.0,
         "fov_override": 30,
         "rot_x": -0.04, "rot_y":  3.14, "rot_z":  0.000},
        # F7 後ろハイアングル引き（見下ろし）
        {"length": 40, "distance": -55.0, "end_distance": -68.0,
         "fov_override": 30,
         "rot_x": -0.50, "rot_y":  3.14, "rot_z":  0.000},
        # F8 後ろ近接ミドル
        {"length": 48, "distance": -20.0, "end_distance": -28.0,
         "fov_override": 30,
         "rot_x": -0.06, "rot_y":  3.14, "rot_z":  0.000},

        # ═══════════════════════════════════════════
        # パターン G (5カット / 196F) FOV60 バリエーション
        # 斜め・横・後ろからの見上げ + 全身ハイ
        # ═══════════════════════════════════════════
        # G1 FOV60 斜め右ローアングル
        {"length": 28, "distance": -20.0, "end_distance": -25.0,
         "fov_override": 60,
         "rot_x":  0.45, "rot_y":  0.30, "rot_z":  0.000,
         "composition": "foot", "pos_y_offset": 1.7},
        # G2 FOV60 横からローアングル右
        {"length": 32, "distance": -22.0, "end_distance": -26.0,
         "fov_override": 60,
         "rot_x":  0.35, "rot_y":  1.10, "rot_z":  0.000,
         "composition": "foot", "pos_y_offset": 1.7},
        # G3 FOV60 後ろからローアングル
        {"length": 28, "distance": -22.0, "end_distance": -26.0,
         "fov_override": 60,
         "rot_x":  0.40, "rot_y":  3.14, "rot_z":  0.000,
         "composition": "foot", "pos_y_offset": 1.7},
        # G4 FOV60 斜め左ローアングル
        {"length": 28, "distance": -20.0, "end_distance": -24.0,
         "fov_override": 60,
         "rot_x":  0.40, "rot_y": -0.30, "rot_z":  0.000,
         "composition": "foot", "pos_y_offset": 1.7},
        # G5 FOV30 全身ハイアングル引き（見下ろし広角）
        {"length": 80, "distance": -30.0, "end_distance": -52.0,
         "fov_override": 30,
         "rot_x": -0.30, "rot_y":  0.00, "rot_z":  0.000,
         "composition": "body"},

        # ═══════════════════════════════════════════
        # パターン H (7カット / 280F) A バリエーション
        # やや左・斜め角度違い・ズームアウト
        # ═══════════════════════════════════════════
        {"length": 24, "distance": -16.0, "end_distance": -19.0,
         "rot_x": -0.05, "rot_y": -0.08, "rot_z":  0.000},
        {"length": 56, "distance": -38.0, "end_distance": -54.0,
         "rot_x": -0.04, "rot_y":  0.22, "rot_z":  0.000},
        {"length": 20, "distance": -18.0, "end_distance": -21.0,
         "rot_x": -0.12, "rot_y":  0.00, "rot_z":  0.000},
        {"length": 40, "distance": -32.0, "end_distance": -50.0,
         "rot_x": -0.05, "rot_y": -0.22, "rot_z":  0.000},
        {"length": 40, "distance": -22.0, "end_distance": -36.0,
         "rot_x": -0.05, "rot_y": -0.38, "rot_z":  0.050},
        {"length": 48, "distance": -18.0, "end_distance": -65.0,
         "rot_x": -0.05, "rot_y":  0.10, "rot_z":  0.000},
        {"length": 52, "distance": -22.0, "end_distance": -57.0,
         "rot_x": -0.04, "rot_y":  0.22, "rot_z":  0.000},

        # ═══════════════════════════════════════════
        # パターン I (5カット / 200F) B バリエーション
        # やや右・後ろズームアウト
        # ═══════════════════════════════════════════
        {"length": 24, "distance": -16.0, "end_distance": -20.0,
         "rot_x": -0.06, "rot_y":  0.10, "rot_z":  0.000},
        {"length": 48, "distance": -40.0, "end_distance": -52.0,
         "rot_x": -0.05, "rot_y":  0.22, "rot_z":  0.000},
        {"length": 32, "distance": -22.0, "end_distance": -40.0,
         "rot_x": -0.05, "rot_y":  0.38, "rot_z": -0.040},
        {"length": 52, "distance": -20.0, "end_distance": -55.0,
         "rot_x": -0.04, "rot_y": -0.22, "rot_z":  0.000},
        {"length": 44, "distance": -45.0, "end_distance": -68.0,
         "fov_override": 30,
         "rot_x": -0.06, "rot_y":  3.14, "rot_z":  0.000},

        # ═══════════════════════════════════════════
        # パターン J (9カット / 340F) C バリエーション
        # 斜め左・ローアングル違い
        # ═══════════════════════════════════════════
        {"length": 20, "distance": -18.0, "end_distance": -22.0,
         "rot_x":  0.18, "rot_y":  0.00, "rot_z":  0.000},
        {"length": 48, "distance": -36.0, "end_distance": -50.0,
         "rot_x": -0.05, "rot_y": -0.22, "rot_z":  0.060},
        {"length": 20, "distance": -14.0, "end_distance": -18.0,
         "rot_x": -0.05, "rot_y": -0.10, "rot_z":  0.000},
        {"length": 56, "distance": -40.0, "end_distance": -54.0,
         "rot_x":  0.10, "rot_y":  0.00, "rot_z":  0.000},
        {"length": 48, "distance": -28.0, "end_distance": -42.0,
         "rot_x":  0.22, "rot_y": -0.38, "rot_z":  0.000},
        {"length": 40, "distance": -26.0, "end_distance": -38.0,
         "rot_x": -0.05, "rot_y": -0.45, "rot_z":  0.050},
        {"length": 48, "distance": -20.0, "end_distance": -48.0,
         "rot_x": -0.05, "rot_y": -0.22, "rot_z":  0.000},
        {"length": 24, "distance": -18.0, "end_distance": -22.0,
         "rot_x": -0.06, "rot_y":  0.12, "rot_z":  0.000},
        {"length": 36, "distance": -36.0, "end_distance": -55.0,
         "rot_x": -0.04, "rot_y": -0.22, "rot_z":  0.000},

        # ═══════════════════════════════════════════
        # パターン K (4カット / 156F) D バリエーション
        # 超クロース角度違い + 超引き斜め
        # ═══════════════════════════════════════════
        {"length": 24, "distance": -18.0, "end_distance": -20.0,
         "fov_override": 15,
         "rot_x": -0.05, "rot_y": -0.10, "rot_z":  0.000},
        {"length": 56, "distance": -90.0, "end_distance": -90.0,
         "fov_override": 30,
         "rot_x": -0.03, "rot_y":  0.22, "rot_z":  0.000},
        {"length": 20, "distance": -18.0, "end_distance": -22.0,
         "fov_override": 15,
         "rot_x": -0.14, "rot_y":  0.00, "rot_z":  0.000},
        {"length": 56, "distance": -90.0, "end_distance": -90.0,
         "fov_override": 30,
         "rot_x": -0.03, "rot_y": -0.22, "rot_z":  0.000},

        # ═══════════════════════════════════════════
        # パターン L (4カット / 164F) E バリエーション
        # 全身斜め + 後ろ斜め見下ろし + 足元斜め
        # ═══════════════════════════════════════════
        {"length": 48, "distance": -90.0, "end_distance": -82.0,
         "fov_override": 30,
         "rot_x": -0.04, "rot_y":  0.22, "rot_z":  0.000,
         "composition": "body"},
        {"length": 24, "distance": -86.0, "end_distance": -78.0,
         "fov_override": 30,
         "rot_x": -0.79, "rot_y":  2.80, "rot_z":  0.000},
        {"length": 64, "distance": -65.0, "end_distance": -55.0,
         "fov_override": 30,
         "rot_x": -0.05, "rot_y": -0.22, "rot_z":  0.000,
         "composition": "body"},
        {"length": 28, "distance": -18.0, "end_distance": -22.0,
         "fov_override": 60,
         "rot_x":  0.524, "rot_y":  0.20, "rot_z":  0.000,
         "composition": "foot", "pos_y_offset": 1.7},

        # ═══════════════════════════════════════════
        # パターン M (5カット / 240F) 横アングル
        # 真横から右・左・ローアングル
        # ═══════════════════════════════════════════
        {"length": 24, "distance": -18.0, "end_distance": -22.0,
         "rot_x": -0.06, "rot_y":  1.57, "rot_z":  0.000},
        {"length": 56, "distance": -38.0, "end_distance": -56.0,
         "rot_x": -0.04, "rot_y":  1.57, "rot_z":  0.000},
        {"length": 20, "distance": -18.0, "end_distance": -22.0,
         "rot_x": -0.06, "rot_y": -1.57, "rot_z":  0.000},
        {"length": 56, "distance": -38.0, "end_distance": -56.0,
         "rot_x": -0.04, "rot_y": -1.57, "rot_z":  0.000},
        {"length": 84, "distance": -28.0, "end_distance": -45.0,
         "rot_x":  0.18, "rot_y":  1.57, "rot_z":  0.000},

        # ═══════════════════════════════════════════
        # パターン N (5カット / 236F) テレフォト近接
        # FOV20-22 + 中距離（圧縮効果）
        # ═══════════════════════════════════════════
        {"length": 48, "distance": -45.0, "end_distance": -40.0,
         "fov_override": 20,
         "rot_x": -0.04, "rot_y":  0.00, "rot_z":  0.000},
        {"length": 48, "distance": -48.0, "end_distance": -42.0,
         "fov_override": 20,
         "rot_x": -0.05, "rot_y":  0.22, "rot_z":  0.000},
        {"length": 48, "distance": -45.0, "end_distance": -40.0,
         "fov_override": 20,
         "rot_x": -0.05, "rot_y": -0.22, "rot_z":  0.000},
        {"length": 44, "distance": -50.0, "end_distance": -42.0,
         "fov_override": 22,
         "rot_x": -0.14, "rot_y":  0.00, "rot_z":  0.000},
        {"length": 48, "distance": -48.0, "end_distance": -42.0,
         "fov_override": 20,
         "rot_x": -0.04, "rot_y":  3.14, "rot_z":  0.000},

        # ═══════════════════════════════════════════
        # パターン O (6カット / 264F) 後ろアングル追加
        # ハイ・ロー・斜め各方向バリエーション
        # ═══════════════════════════════════════════
        # O1 後ろ斜め右ハイ（見下ろし）
        {"length": 32, "distance": -55.0, "end_distance": -65.0,
         "fov_override": 30,
         "rot_x": -0.45, "rot_y":  2.80, "rot_z":  0.000},
        # O2 後ろ斜め左ハイ（見下ろし）
        {"length": 32, "distance": -50.0, "end_distance": -60.0,
         "fov_override": 30,
         "rot_x": -0.45, "rot_y": -2.80, "rot_z":  0.000},
        # O3 後ろ近接アップ（pos_y_offset+2.0）
        {"length": 24, "distance": -20.0, "end_distance": -26.0,
         "fov_override": 30,
         "rot_x": -0.06, "rot_y":  3.14, "rot_z":  0.000,
         "pos_y_offset": 2.0},
        # O4 後ろ斜め右ローアングル（見上げ）
        {"length": 48, "distance": -28.0, "end_distance": -40.0,
         "fov_override": 30,
         "rot_x":  0.15, "rot_y":  2.36, "rot_z":  0.000},
        # O5 後ろ斜め左ローアングル（見上げ）
        {"length": 48, "distance": -28.0, "end_distance": -40.0,
         "fov_override": 30,
         "rot_x":  0.15, "rot_y": -2.36, "rot_z":  0.000},
        # O6 後ろ全身テレフォト（body）
        {"length": 80, "distance": -70.0, "end_distance": -60.0,
         "fov_override": 30,
         "rot_x": -0.04, "rot_y":  3.14, "rot_z":  0.000,
         "composition": "body"},

        # ═══════════════════════════════════════════
        # パターン P (5カット / 280F) 遠距離変化
        # 超引き + アップとのメリハリ
        # ═══════════════════════════════════════════
        # P1 超引き・斜め右（FOV30）
        {"length": 56, "distance": -75.0, "end_distance": -88.0,
         "fov_override": 30,
         "rot_x": -0.03, "rot_y":  0.38, "rot_z":  0.000},
        # P2 全身引き・斜め左（FOV30 body）
        {"length": 56, "distance": -70.0, "end_distance": -82.0,
         "fov_override": 30,
         "rot_x": -0.04, "rot_y": -0.38, "rot_z":  0.000,
         "composition": "body"},
        # P3 アップ・斜め左ハイアングル
        {"length": 24, "distance": -16.0, "end_distance": -20.0,
         "rot_x": -0.18, "rot_y": -0.22, "rot_z":  0.000},
        # P4 超引き・正面全身（FOV30 body）
        {"length": 64, "distance": -85.0, "end_distance": -95.0,
         "fov_override": 30,
         "rot_x": -0.03, "rot_y":  0.00, "rot_z":  0.000,
         "composition": "body"},
        # P5 超引き・斜め右全身（FOV30 body）
        {"length": 80, "distance": -80.0, "end_distance": -95.0,
         "fov_override": 30,
         "rot_x": -0.03, "rot_y":  0.22, "rot_z":  0.000,
         "composition": "body"},

    ]

    # 全カットに S字補間を適用
    for cd in cut_defs:
        cd["s_curve"] = True

    # ── イントロ静止ショット ──
    # 40フレーム以上の静止が検出された場合のみ適用
    intro_shot = {
        "distance":     -60.0,
        "end_distance": -56.0,
        "rot_x": -0.04, "rot_y": 0.0, "rot_z": 0.0,
        "composition": "body",
    }

    return generate_cuts(bones, char_height_mmd, fov_base, cut_defs, total,
                         intro_cut=intro_shot)
