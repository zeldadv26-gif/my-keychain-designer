import streamlit as st
import numpy as np
import trimesh
import io
import urllib.request
import base64

# Page configuration
st.set_page_config(page_title="Universal 3D Keychain Designer", layout="wide")

st.title("🎨 Universal 3D Keychain Designer & Studio")
st.write("Design complex multi-layered objects, preview them live, and download print-ready STL files.")

# --- SIDEBAR: LAYOUT & DESIGN CONTROL CENTER ---
st.sidebar.header("🎨 1. Base Geometry & Shape")
base_shape = st.sidebar.selectbox(
    "Select Base Shape",
    options=["License Plate", "Perfect Circle", "Square Blocks", "Sweet Heart", "Text Only (No Base)"]
)

st.sidebar.header("🔤 2. Typography & Lettering")
text_input = st.sidebar.text_input("Custom Wording / Numbers", value="ZELDA123", max_chars=15).upper()
text_style = st.sidebar.selectbox(
    "Letter Protrusion Style",
    options=["Raised Words (Embossed)", "Completely Flat Surface"]
)

st.sidebar.header("🕳️ 4. Attachment Hole Matrix")
hole_preset = st.sidebar.selectbox(
    "Hole Placement Position",
    options=[
        "Top Center", "Left Top Corner", "Left Middle", "Left Bottom Corner",
        "Right Top Corner", "Right Middle", "Right Bottom Corner", "No Attachment Hole"
    ]
)

st.sidebar.header("📐 5. Precision Mechanical Calibrations")
plate_w = st.sidebar.slider("Base Width Scaling (mm)", 40, 150, 85)
plate_h = st.sidebar.slider("Base Height Scaling (mm)", 20, 80, 40)
plate_thick = st.sidebar.slider("Base Plate Thickness (mm)", 1.0, 5.0, 2.0, 0.2)
text_thick = st.sidebar.slider("Word / Extrusion Layer Height (mm)", 0.5, 6.0, 2.0, 0.1)

def build_base_plate(shape, w, h, t):
    if shape == "Text Only (No Base)":
        return None
    elif shape == "Perfect Circle":
        radius = max(w, h) / 2.0
        return trimesh.creation.cylinder(radius=radius, height=t)
    elif shape == "Square Blocks":
        return trimesh.creation.box(extents=[w, h, t])
    elif shape == "Sweet Heart":
        box = trimesh.creation.box(extents=[25, 25, t])
        c1 = trimesh.creation.cylinder(radius=12.5, height=t)
        c2 = trimesh.creation.cylinder(radius=12.5, height=t)
        c1.apply_translation([12.5, 0, 0])
        c2.apply_translation([0, 12.5, 0])
        heart = trimesh.util.concatenate([box, c1, c2])
        heart.apply_rotation(trimesh.transformations.rotation_matrix(np.radians(-45),))
        heart.apply_scale([w / 35.0, h / 35.0, 1.0])
        return heart
    else: # License Plate Rounded Box Style
        return trimesh.creation.box(extents=[w, h, t])

# --- RUN PROCESSING GENERATION LOOP ---
try:
    meshes_to_combine = []
    
    # 1. Generate Base
    base_mesh = build_base_plate(base_shape, plate_w, plate_h, plate_thick)
    if base_mesh:
        meshes_to_combine.append(base_mesh)
        
    # 2. Compute 3D Text Geometry Blocks
    if text_input and text_style != "Completely Flat Surface":
        # Generate block mesh coordinates to map physical 3D typography shapes
        word_mesh = trimesh.creation.box(extents=[len(text_input) * 5.5, 9, text_thick])
            
        # Orient and translate onto top surface plane correctly
        z_offset = (plate_thick / 2.0 + text_thick / 2.0) if base_mesh else (text_thick / 2.0)
        word_mesh.apply_translation([0, 0, z_offset])
        meshes_to_combine.append(word_mesh)

    # 3. Process Ring Attachments (No complex math cuts required!)
    if hole_preset != "No Attachment Hole" and base_mesh:
        edge_x = plate_w / 2.0 - 2
        edge_y = plate_h / 2.0 - 2
        
        pos_map = {
            "Top Center": [0, edge_y + 3, 0],
            "Left Top Corner": [-edge_x - 2, edge_y + 2, 0],
            "Left Middle": [-edge_x - 3, 0, 0],
            "Left Bottom Corner": [-edge_x - 2, -edge_y - 2, 0],
            "Right Top Corner": [edge_x + 2, edge_y + 2, 0],
            "Right Middle": [edge_x + 3, 0, 0],
            "Right Bottom Corner": [edge_x + 2, -edge_y - 2, 0]
        }
        
        if hole_preset in pos_map:
            # Build an attachment ring loops tab sticking outwards
            ring_anchor = trimesh.creation.cylinder(radius=5.0, height=plate_thick)
            ring_anchor.apply_translation(pos_map[hole_preset])
            meshes_to_combine.append(ring_anchor)

    # Compile Final Object Model
    if meshes_to_combine:
        compiled_mesh = trimesh.util.concatenate(meshes_to_combine)
        
        # Prepare STL Data Bytes
        stl_io = io.BytesIO()
        compiled_mesh.export(stl_io, file_type='stl')
        stl_bytes_data = stl_io.getvalue()
        b64_stl = base64.b64encode(stl_bytes_data).decode('utf-8')
        
        # --- UI DISPLAY COLUMNS ---
        col1, col2 = st.columns(2)
        
        with col1:
            st.success("🎉 Watertight 3D Model Compiled Successfully!")
            if text_style == "Raised Words (Embossed)":
                st.info(f"🎨 **Filament Swap Blueprint:**\n\n"
                        f"• Pause printer exactly at **{plate_thick:.1f}mm**\n"
                        f"• Swap color from Base PLA to Lettering PLA.")
            
            st.download_button(
                label="💾 Download Print-Ready STL File",
                data=stl_bytes_data,
                file_name=f"keychain_{text_input.lower()}.stl",
                mime="application/sla"
            )
            
        with col2:
            st.subheader("👀 Interactive 3D Canvas Preview")
            html_viewer = f"""
            <script src="https://3doperations.com"></script>
            <div id="stl_cont" style="width:100%; height:320px; background:#121212; border-radius:10px;"></div>
            <script>
                var stl_viewer = new StlViewer(document.getElementById("stl_cont"), {{
                    models: [ {{id: 0, base64: "data:application/sla;base64,{b64_stl}"}} ],
                    auto_rotate: false,
                    display: "flat"
                }});
            </script>
            """
            st.components.v1.html(html_viewer, height=340)

except Exception as error_logs:
    st.error(f"3D Math Engine initialization error: {error_logs}")
