# app.py
import streamlit as st
# 埋め込み時の余分な余白やフッターを消すCSS
hide_streamlit_style = """
<style>
/* Streamlitの右上のメニュー非表示 */
#MainMenu {visibility: hidden;}
/* フッターを非表示 */
footer {visibility: hidden;}
/* ヘッダー部分を非表示 */
header {visibility: hidden;}
/* iframe内のパディングを調整して外枠をスッキリさせる */
.block-container {
    padding-top: 0rem;
    padding-right: 1rem;
    padding-left: 1rem;
    padding-bottom: 0rem;
}
</style>
"""
st.markdown(hide_streamlit_style, unsafe_allow_html=True)
from vmd_writer import write_vmd
from vmd_reader import (read_vmd_bones, get_total_frames,
                         get_safety, get_detected_bones_report)
from camera_core import get_target, dist_to_fov
from camera_modes import drift
from camera_modes import driftmode
from camera_modes import slowmode
from camera_modes import animemode

st.set_page_config(
    page_title="MMD Camera Tool",
    page_icon="🎬", layout="wide"
)

st.title("🎬 MMD 自動カメラモーション生成ツール")
st.divider()

# ── ① ファイルアップローダー ──
st.subheader("📂 ダンスVMDファイルの読み込み")

uploaded = st.file_uploader(
    "ダンスモーションのVMDをここにドロップ",
    type=["vmd"],
)

bones        = {}
total_frames = 0

if uploaded is not None:
    dance_data = uploaded.read()
    with st.spinner("VMDを解析中..."):
        bones = read_vmd_bones(dance_data)
    total_frames = get_total_frames(bones)
    report       = get_detected_bones_report(bones)

    st.success(
        f"✅ 読み込み成功！  総フレーム数: **{total_frames}**"
    )

    with st.expander("🦴 検出されたボーン一覧（フレーム数付き）", expanded=True):
        PRIORITY = [
            "全ての親", "グルーブ", "センター",
            "左足ＩＫ", "右足ＩＫ",
            "上半身", "下半身", "腰",
            "右手首", "左手首",
            "右足首", "左足首",
        ]

        st.markdown("**📍 位置ボーン**")
        col1, col2 = st.columns(2)

        with col1:
            for b in PRIORITY:
                cnt = report["pos"].get(b, 0)
                if cnt > 0:
                    st.write(f"✅ {b}：{cnt} フレーム")
                else:
                    st.write(f"⬜ {b}：未検出")

        with col2:
            others = {k: v for k, v in report["pos"].items()
                      if k not in PRIORITY}
            for b, cnt in sorted(others.items()):
                st.write(f"　{b}：{cnt} フレーム")

        st.markdown("**🔄 回転ボーン**")
        for b, cnt in sorted(report["rot"].items()):
            st.write(f"✅ {b}：{cnt} フレーム")

else:
    st.info("💡 まずダンスモーションのVMDを読み込んでください。")

st.divider()

# ── ② 設定 ──
st.subheader("⚙️ キャラクター・カメラ設定")

col_s1, col_s2, col_s3 = st.columns(3)
with col_s1:
    char_height_cm = st.number_input(
        "キャラクターの身長（cm）",
        min_value=100, max_value=200,
        value=158, step=1,
    )
    char_height_mmd = char_height_cm / 10.0
    st.caption(f"MMD単位: {char_height_mmd:.1f}  頭の高さ推定: {char_height_mmd*0.88:.2f}")

with col_s2:
    fov_base = st.slider(
        "視野角 FOV 基本値",
        min_value=10, max_value=60, value=30, step=1,
        help="30=標準。小さいほど望遠（アップ気味）になります。",
    )

with col_s3:
    dist_scale = st.slider(
        "距離調整",
        min_value=0.5, max_value=2.0, value=1.0, step=0.05,
        help="1.0=標準。大きいほど遠く（引き）、小さいほど近く（寄り）になります。",
    )
    st.caption(f"{'近め ◀' if dist_scale < 1.0 else ('▶ 遠め' if dist_scale > 1.0 else '標準')}")

if bones:
    with st.expander("🔍 フレーム0 状態プレビュー"):
        tgt0 = get_target(bones, 0, char_height_mmd, -35.0, -0.08)
        s0   = get_safety(bones, 0, char_height_mmd)
        st.write(f"- 注視点 X: {tgt0['pos_x']:.3f}")
        st.write(f"- 注視点 Y: {tgt0['pos_y']:.3f}")
        st.write(f"- 注視点 Z: {tgt0['pos_z']:.3f}")
        st.write(f"- 実効距離: {tgt0['distance']:.2f}")
        st.write(f"- FOV: {dist_to_fov(tgt0['distance'], fov_base)}")
        st.write(f"- セーフティpull: {s0['pull']:.2f}")
        st.write(f"- ドアップ禁止: {s0['is_busy']}")

st.divider()

# ── ③ モード選択 & 生成 ──
st.subheader("🎬 カメラモーションを生成")

col_m1, col_m2, col_m3, col_m4 = st.columns(4)

with col_m1:
    st.markdown("**⚡ スピードモード**")
    st.write("テンポよくカットが切り替わる、ライブ映像のような演出。アップ・引き・後ろアングルをサクサク切り替えます。")

with col_m2:
    st.markdown("**🌊 ドリフトモード**")
    st.write("カメラが1方向にふわりと流れ、向きが変わる瞬間にカット。ズームイン・アウト・横流し・回り込みをSカーブ補間で優雅に。")

with col_m3:
    st.markdown("**🌸 ゆっくりモード**")
    st.write("望遠FOV12固定・引き多用のアニメ風演出。ゆったりしたカメラワークで落ち着いた雰囲気に。")

with col_m4:
    st.markdown("**🎌 アニメモード**")
    st.write("1カット1動作のアニメ的構成。パン・ズームイン・ズームアウト・静止を一方向ずつ。FOV12望遠でアニメらしい圧縮感。")

st.write("")

btn_col1, btn_col2, btn_col3, btn_col4 = st.columns(4)

with btn_col1:
    gen_speed = st.button(
        "⚡ スピードモードで生成",
        type="primary",
        use_container_width=True,
        disabled=(not bones),
    )

with btn_col2:
    gen_drift = st.button(
        "🌊 ドリフトモードで生成",
        type="primary",
        use_container_width=True,
        disabled=(not bones),
    )

with btn_col3:
    gen_slow = st.button(
        "🌸 ゆっくりモードで生成",
        type="primary",
        use_container_width=True,
        disabled=(not bones),
    )

with btn_col4:
    gen_anime = st.button(
        "🎌 アニメモードで生成",
        type="primary",
        use_container_width=True,
        disabled=(not bones),
    )

st.divider()

# ── 生成処理 ──
def _apply_dist_scale(frames, scale):
    """全フレームの distance に scale を掛けて遠近を調整する"""
    if scale == 1.0:
        return frames
    for f in frames:
        f["distance"] = f["distance"] * scale
    return frames

def _show_result(frames, filename):
    if not frames:
        st.error("フレームが生成されませんでした。")
        return
    vmd_bytes = write_vmd(frames)
    st.success(f"✅ 生成完了！  キーフレーム数: {len(frames)}")
    st.download_button(
        label=f"💾 {filename} をダウンロード",
        data=vmd_bytes,
        file_name=filename,
        mime="application/octet-stream",
        use_container_width=True,
        type="primary",
    )
    with st.expander("📊 生成内容の詳細"):
        st.write(f"- 身長: {char_height_cm}cm  MMD単位: {char_height_mmd:.1f}")
        st.write(f"- 基本FOV: {fov_base}")
        st.write(f"- キーフレーム数: {len(frames)}")
        st.write(f"- ファイルサイズ: {len(vmd_bytes):,} バイト")
        fov_list  = [f["fov"] for f in frames]
        dist_list = [f["distance"] for f in frames]
        st.write(f"- FOV 範囲: {min(fov_list)} ～ {max(fov_list)}")
        st.write(f"- Distance 範囲: {min(dist_list):.1f} ～ {max(dist_list):.1f}")
        st.write("最初の8フレームのプレビュー:")
        for f in frames[:8]:
            st.write(f"  [{f['frame']}] X={f['pos_x']:.2f} Y={f['pos_y']:.2f} dist={f['distance']:.1f} FOV={f['fov']}")

if gen_speed:
    with st.spinner("スピードモードで生成中..."):
        frames = drift.generate(char_height_mmd, bones, fov_base)
    _show_result(_apply_dist_scale(frames, dist_scale), "camera_speed.vmd")

if gen_drift:
    with st.spinner("ドリフトモードで生成中..."):
        frames = driftmode.generate(char_height_mmd, bones, fov_base)
    _show_result(_apply_dist_scale(frames, dist_scale), "camera_drift.vmd")

if gen_slow:
    with st.spinner("ゆっくりモードで生成中..."):
        frames = slowmode.generate(char_height_mmd, bones, fov_base)
    _show_result(_apply_dist_scale(frames, dist_scale), "camera_slow.vmd")

if gen_anime:
    with st.spinner("アニメモードで生成中..."):
        frames = animemode.generate(char_height_mmd, bones, fov_base)
    _show_result(_apply_dist_scale(frames, dist_scale), "camera_anime.vmd")
