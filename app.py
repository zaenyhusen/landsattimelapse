import streamlit as st
import ee
import folium
import cv2
import os
from streamlit_folium import st_folium
from folium.plugins import Draw
from utils.gee_processing import initialize_gee, get_annual_composite, apply_visualization, MISSION_PRIORITY
from utils.video_export import image_to_numpy, frames_to_mp4

st.set_page_config(page_title="EarthTimelapse", layout="wide")
initialize_gee()

st.title("EarthTimelapse — Satellite Timelapse Generator")

with st.sidebar:
    st.header("Control Panel")

    year_start, year_end = st.slider("Temporal Range", 1990, 2025, (2000, 2024))

    st.markdown("**Satellite Missions**")
    use_l5 = st.checkbox("Landsat 5 (1984–2013)", value=True)
    use_l7 = st.checkbox("Landsat 7 (1999–2022)", value=False)
    use_l8 = st.checkbox("Landsat 8 (2013–present)", value=True)
    use_l9 = st.checkbox("Landsat 9 (2021–present)", value=True)

    band_combo = st.selectbox(
        "Spectral Visualization",
        ['Natural Color', 'False Color NIR', 'SWIR Composite', 'NDVI', 'NDWI']
    )

    fps = st.slider("Video FPS", 1, 10, 3)
    generate = st.button("Generate Timelapse", use_container_width=True)

selected_missions = []
if use_l5: selected_missions.append('L5')
if use_l7: selected_missions.append('L7')
if use_l8: selected_missions.append('L8')
if use_l9: selected_missions.append('L9')

st.subheader("🗺️ Define Area of Interest (AOI)")

m = folium.Map(location=[0, 117], zoom_start=5, tiles="Esri.WorldImagery")
Draw(export=True, draw_options={
    'polyline': False, 'circle': False,
    'marker': False, 'circlemarker': False
}).add_to(m)

map_data = st_folium(m, height=450, width=None)

aoi_geojson = None
if map_data and map_data.get("last_active_drawing"):
    import ee
    coords = map_data["last_active_drawing"]["geometry"]["coordinates"][0]
    aoi_geojson = ee.Geometry.Polygon(coords)

if generate:
    if aoi_geojson is None:
        st.warning("Gambar AOI dulu di peta menggunakan polygon tool.")
    elif not selected_missions:
        st.warning("Pilih minimal 1 misi satelit.")
    else:
        years  = list(range(year_start, year_end + 1))
        frames = []
        skipped = []

        log_col  = st.expander("Processing Log", expanded=True)
        progress = st.progress(0)
        status   = st.empty()

        for i, year in enumerate(years):
            status.text(f"Processing {year}...")

            active = MISSION_PRIORITY.get(year, ['L8'])
            missions_for_year = [m for m in selected_missions if m in active]

            if not missions_for_year:
                skipped.append(year)
                log_col.write(f"{year}: tidak ada misi sesuai, dilewati")
                progress.progress((i + 1) / len(years))
                continue

            composite, used = get_annual_composite(year, aoi_geojson, missions_for_year)

            if composite is None:
                skipped.append(year)
                log_col.write(f"{year}: tidak ada data tersedia")
                progress.progress((i + 1) / len(years))
                continue

            img_vis, vis_params = apply_visualization(composite, band_combo)
            frame = image_to_numpy(img_vis, aoi_geojson, vis_params)

            # Tambah label tahun
            frame_copy = frame.copy()
            cv2.putText(frame_copy, str(year), (20, 50),
                        cv2.FONT_HERSHEY_SIMPLEX, 1.5, (255, 255, 255), 3)
            frames.append(frame_copy)
            log_col.write(f"✅ {year}: {' + '.join(used)}")
            progress.progress((i + 1) / len(years))

        if frames:
            output_path = "outputs/timelapse.mp4"
            os.makedirs("outputs", exist_ok=True)
            frames_to_mp4(frames, output_path, fps=fps)

            status.success(f"✅ Selesai! {len(frames)} frame, {len(skipped)} tahun dilewati.")
            with open(output_path, "rb") as f:
                st.download_button("⬇️ Download MP4", f,
                                   file_name="timelapse.mp4", mime="video/mp4")
            with open(output_path, "rb") as video_file:
                video_bytes = video_file.read()
            st.video(video_bytes)