import streamlit as st
from PIL import Image
import io
import hashlib
import base64

from platemaker_module import PlateMaker
from google_drive_uploader import DriveUploader

st.set_page_config(page_title="Shobha Sarees Platemaker Dashboard", layout="wide")
st.title("🎨 Shobha Sarees Platemaker Dashboard")

# -----------------------------------------------------------------------------
# Services (unchanged contracts)
# -----------------------------------------------------------------------------
@st.cache_resource
def init_services():
    return PlateMaker(), DriveUploader()

platemaker, drive_uploader = init_services()

# -----------------------------------------------------------------------------
# Constants
# -----------------------------------------------------------------------------
CATALOG_OPTIONS = [
    "Blueberry",
    "Lavanya",
    "Soundarya",
    "Malai Crape",
    "Sweet Sixteen",
    "Heritage"
    "Srivalli",
    "Shakuntala",
]
DEFAULT_SUGGEST_START = 4000

# -----------------------------------------------------------------------------
# Session state init
# -----------------------------------------------------------------------------
# Batch mode
if "batch_rows" not in st.session_state:
    # uid -> row dict (kept internal, not displayed)
    st.session_state["batch_rows"] = {}
if "batch_row_order" not in st.session_state:
    # list of uids in display order
    st.session_state["batch_row_order"] = []
if "batch_results" not in st.session_state:
    st.session_state["batch_results"] = None
if "batch_editor_version" not in st.session_state:
    st.session_state["batch_editor_version"] = 0
if "batch_base_number" not in st.session_state:
    st.session_state["batch_base_number"] = DEFAULT_SUGGEST_START

# Simple mode
if "simple_design_numbers" not in st.session_state:
    st.session_state["simple_design_numbers"] = {}

# -----------------------------------------------------------------------------
# Helpers
# -----------------------------------------------------------------------------
def file_uid(f):
    try:
        head = f.read(512)
        f.seek(0)
        h = hashlib.md5(head).hexdigest()
        return f"{f.name}:{f.size}:{h}"
    except Exception:
        return f"{f.name}:{getattr(f, 'size', 'na')}"

def make_preview_data_url(uploaded_file, max_size=(140, 140), quality=60):
    try:
        uploaded_file.seek(0)
        img = Image.open(uploaded_file).convert("RGB")
        img.thumbnail(max_size)
        buf = io.BytesIO()
        img.save(buf, format="JPEG", quality=quality)
        b64 = base64.b64encode(buf.getvalue()).decode("utf-8")
        uploaded_file.seek(0)
        return f"data:image/jpeg;base64,{b64}"
    except Exception:
        uploaded_file.seek(0)
        return ""

def derive_fields(catalog, dn):
    dn_s = str(dn).strip()
    banner = f"{catalog} 6.30 D.No {dn_s}" if catalog and dn_s else ""
    output = f"{catalog} - {dn_s}.jpg" if catalog and dn_s else ""
    folder = f"Shobha Sarees/{catalog}/" if catalog else ""
    return banner, output, folder

def process_and_upload_image(uploaded_file, catalog, design_number, status_cb):
    uploaded_file.seek(0)
    status_cb("🚀 Starting processing...")
    processed_img = platemaker.process_image(
        uploaded_file,
        catalog,
        design_number,
        status_callback=status_cb,
    )
    output_filename = f"{catalog} - {design_number}.jpg"
    status_cb("💾 Converting to upload format...")
    img_bytes = io.BytesIO()
    processed_img.save(img_bytes, format="JPEG", quality=100)
    img_bytes.seek(0)
    status_cb("☁️ Uploading to Google Drive...")
    drive_url = drive_uploader.upload_image(
        img_bytes,
        output_filename,
        catalog,
    )
    status_cb("✅ Uploaded • [Drive](" + drive_url + ")")
    return output_filename, drive_url

# -----------------------------------------------------------------------------
# Top navigation
# -----------------------------------------------------------------------------
tab_batch, tab_simple = st.tabs(["📦 Batch", "📁 Simple"])

# =============================================================================
# Batch Mode
# =============================================================================
with tab_batch:
    has_results = bool(st.session_state.get("batch_results"))
    if has_results:
        editor_tab, links_tab = st.tabs(["Editor", "Drive links"])
    else:
        editor_tab = st.container()
        links_tab = None

    with editor_tab:
        st.subheader("Upload images")
        batch_files = st.file_uploader(
            "Upload images for batch processing",
            accept_multiple_files=True,
            type=["png", "jpg", "jpeg"],
            key="batch_uploader",
        )

        # Sync rows to uploads (start empty per row)
        current_uids = []
        if batch_files:
            for uf in batch_files:
                uid = file_uid(uf)
                current_uids.append(uid)
                if uid not in st.session_state["batch_rows"]:
                    preview = make_preview_data_url(uf)
                    st.session_state["batch_rows"][uid] = {
                        "preview": preview,
                        "catalog": "",
                        "design_number": "",
                        "banner_preview": "",
                        "output_name": "",
                        "target_folder": "",
                    }
            st.session_state["batch_row_order"] = current_uids

        # Prune removed
        to_prune = [uid for uid in list(st.session_state["batch_rows"].keys()) if uid not in current_uids]
        for uid in to_prune:
            st.session_state["batch_rows"].pop(uid, None)
        if not batch_files:
            st.session_state["batch_row_order"] = []

        # ===== Two-column control bar with expanders =====
        if batch_files:
            col_default, col_numbering = st.columns([1, 1])
            
            # Left column: Choose default catalog expander
            with col_default:
                with st.expander("Choose default", expanded=False):
                    bulk_catalog = st.selectbox(
                        "Default catalog for this batch",
                        options=[""] + CATALOG_OPTIONS,
                        index=0,
                        help="Apply once to set Catalog for all rows; manual per-row changes remain allowed.",
                        key="batch_bulk_catalog",
                    )
                    if st.button("✅ Apply to all", use_container_width=True, key="batch_apply_default_catalog"):
                        for uid in st.session_state["batch_row_order"]:
                            row = st.session_state["batch_rows"][uid]
                            row["catalog"] = bulk_catalog
                            b, o, f = derive_fields(row["catalog"], row["design_number"])
                            row["banner_preview"], row["output_name"], row["target_folder"] = b, o, f
                        st.session_state["batch_editor_version"] += 1
                        st.toast("Applied catalog to all rows", icon="✅")
                        st.rerun()
            
            # Right column: Numbering assistant expander (using your exact working logic)
            with col_numbering:
                with st.expander("Numbering assistant", expanded=False):
                    base_number = st.number_input(
                        "Base number",
                        min_value=1,
                        value=st.session_state["batch_base_number"],
                        step=1,
                        help="Suggestions are generated per catalog; existing values are kept.",
                        key="batch_base_input",
                    )
                    if st.button("✨ Apply suggestions (fill blanks only)", key="batch_apply_suggestions"):
                        counters = {c: 0 for c in CATALOG_OPTIONS}
                        # Initialize counters from existing numeric values (adapted for batch_rows)
                        for uid in current_uids:
                            meta = st.session_state["batch_rows"][uid]
                            dn = str(meta.get("design_number", "")).strip()
                            cat = meta.get("catalog")
                            if dn.isdigit() and cat in counters:
                                counters[cat] = max(counters[cat], int(dn) - base_number + 1)
                        # Fill blanks
                        for uid in current_uids:
                            meta = st.session_state["batch_rows"][uid]
                            if not str(meta.get("design_number", "")).strip():
                                cat = meta.get("catalog")
                                if cat in counters:
                                    suggestion = base_number + counters[cat]
                                    meta["design_number"] = str(suggestion)
                                    counters[cat] += 1
                                    # Update derived fields
                                    b, o, f = derive_fields(cat, suggestion)
                                    meta["banner_preview"], meta["output_name"], meta["target_folder"] = b, o, f
                        st.session_state["batch_base_number"] = base_number
                        st.session_state["batch_editor_version"] += 1
                        st.success("Suggestions applied to empty Design No. cells.")
                        st.rerun()

        # Compact (mobile) view default ON
        compact = st.checkbox("Compact view (mobile)", value=True, help="Show only Preview, Catalog, and Design No.")

        if batch_files:
            # Build display data (no technical IDs in UI)
            display_rows = []
            for uid in st.session_state["batch_row_order"]:
                base = st.session_state["batch_rows"][uid]
                b, o, f = derive_fields(base["catalog"], base["design_number"])
                base["banner_preview"], base["output_name"], base["target_folder"] = b, o, f
                display_rows.append(
                    {
                        "preview": base["preview"],
                        "catalog": base["catalog"],
                        "design_number": base["design_number"],
                        "banner_preview": base["banner_preview"],
                        "output_name": base["output_name"],
                        "target_folder": base["target_folder"],
                    }
                )

            # Editor key with version to force refresh after autofill/bulk-apply
            editor_key = f"batch_editor_{st.session_state['batch_editor_version']}"

            def on_batch_edit(local_key=editor_key):
                changes = st.session_state.get(local_key)
                edits = (changes or {}).get("edited_rows", {})
                index_to_uid = st.session_state["batch_row_order"]
                for idx_str, delta in edits.items():
                    try:
                        idx = int(idx_str)
                    except Exception:
                        continue
                    if 0 <= idx < len(index_to_uid):
                        uid = index_to_uid[idx]
                        row = st.session_state["batch_rows"].get(uid)
                        if not row:
                            continue
                        if "catalog" in delta:
                            row["catalog"] = str(delta["catalog"]).strip()
                        if "design_number" in delta:
                            row["design_number"] = str(delta["design_number"]).strip()
                        b, o, f = derive_fields(row["catalog"], row["design_number"])
                        row["banner_preview"], row["output_name"], row["target_folder"] = b, o, f

            base_config = {
                "preview": st.column_config.ImageColumn("Preview", width="small", help="Thumbnail"),
                "catalog": st.column_config.SelectboxColumn(
                    "Catalog", options=CATALOG_OPTIONS, required=True, width="medium", help="Destination catalog"
                ),
                "design_number": st.column_config.TextColumn("Design No.", help="Enter the design number"),
            }
            detail_config = {
                "banner_preview": st.column_config.TextColumn("Banner (preview)", disabled=True),
                "output_name": st.column_config.TextColumn("Output file", disabled=True),
                "target_folder": st.column_config.TextColumn("Drive folder", disabled=True),
            }
            col_config = {**base_config} if compact else {**base_config, **detail_config}
            col_order = ["preview", "catalog", "design_number"] if compact else [
                "preview", "catalog", "design_number", "banner_preview", "output_name", "target_folder"
            ]

            st.data_editor(
                display_rows,
                hide_index=True,
                use_container_width=True,
                column_config=col_config,
                column_order=col_order,
                num_rows="fixed",
                key=editor_key,
                on_change=on_batch_edit,
            )

        st.divider()
        if st.button("🚀 Process & Upload (Batch)", type="primary", use_container_width=True, key="batch_submit"):
            if not batch_files:
                st.error("❌ Please upload at least one image first.")
            else:
                # Validate
                missing = []
                per_uid = {}
                for uf in batch_files:
                    uid = file_uid(uf)
                    row = st.session_state["batch_rows"].get(uid)
                    if not row:
                        missing.append(f"{uf.name} (no row)")
                        continue
                    cat = str(row.get("catalog", "")).strip()
                    dn = str(row.get("design_number", "")).strip()
                    if not cat or not dn:
                        missing.append(f"{uf.name} (catalog/design missing)")
                    per_uid[uid] = {"file": uf, "catalog": cat, "design_number": dn}

                if missing:
                    st.error("❌ Please complete required fields:\n- " + "\n- ".join(missing))
                else:
                    boxes = [st.empty() for _ in batch_files]
                    progress = st.progress(0.0)
                    results = []

                    for idx, uf in enumerate(batch_files):
                        uid = file_uid(uf)
                        info = per_uid[uid]
                        cat = info["catalog"]
                        dn = info["design_number"]
                        box = boxes[idx]

                        def cb(msg, i=idx, b=box):
                            b.markdown(f"Image {i+1}: {msg}")

                        try:
                            filename, url = process_and_upload_image(uf, cat, dn, cb)
                            box.markdown(f"Image {idx+1}: ✅ Uploaded • [Drive]({url})")
                            results.append({"filename": filename, "catalog": cat, "url": url, "status": "success"})
                        except Exception as e:
                            box.error(f"Image {idx+1}: ❌ Error: {e}")
                            results.append({"filename": f"Image {idx+1}", "catalog": cat, "url": None, "status": "error", "error": str(e)})

                        progress.progress((idx + 1) / len(batch_files))

                    successful = [r for r in results if r["status"] == "success"]
                    failed = [r for r in results if r["status"] == "error"]

                    if successful:
                        st.toast("Batch upload complete", icon="✅")
                        st.success(f"✅ Successfully processed {len(successful)} image(s)!")
                        for r in successful:
                            st.success(f"📁 {r['filename']} → `Shobha Sarees/{r['catalog']}/` • [Drive]({r['url']})")
                    if failed:
                        st.error(f"❌ Failed to process {len(failed)} image(s):")
                        for r in failed:
                            st.error(f"• {r['filename']} → {r.get('error', 'Unknown error')}")

                    st.session_state["batch_results"] = results
                    if results and all(r["status"] == "success" for r in results):
                        st.balloons()
                    st.rerun()

    # Hidden links tab shows only after a run
    if has_results and links_tab is not None:
        with links_tab:
            st.subheader("Drive links")
            results = st.session_state.get("batch_results") or []
            success_rows = [r for r in results if r.get("status") == "success"]
            if success_rows:
                for r in success_rows:
                    st.write(f"• {r['filename']} → [Drive]({r['url']})")
            else:
                st.info("No successful uploads in last run.")

# =============================================================================
# Simple Mode (unchanged processing flow)
# =============================================================================
with tab_simple:
    st.subheader("Catalog Settings")
    selected_catalog = st.selectbox(
        "📁 Select Catalog (for all images)",
        CATALOG_OPTIONS,
        index=0,
        key="simple_catalog",
    )

    st.subheader("Upload Saree Images")
    simple_files = st.file_uploader(
        "Choose saree design images",
        accept_multiple_files=True,
        type=["png", "jpg", "jpeg"],
        key="simple_uploader",
    )

    cL, cR = st.columns([6, 1])
   

    if simple_files:
        st.subheader("📸 Preview Images & Set Design Numbers")
        for idx, uploaded_file in enumerate(simple_files):
            col1, col2 = st.columns([1, 1])
            with col1:
                try:
                    image = Image.open(uploaded_file)
                    st.image(image, use_column_width=True)
                except Exception as e:
                    st.warning(f"Could not preview Image {idx + 1}: {uploaded_file.name} ({e})")
                st.caption(f"Image {idx + 1}: {uploaded_file.name}")

            with col2:
                design_key = f"simple_design_{idx}_{uploaded_file.name}"
                design_number = st.text_input(
                    f"Design Number for Image {idx + 1}:",
                    key=design_key,
                    placeholder="e.g., 4290",
                )
                st.session_state["simple_design_numbers"][idx] = design_number

                if selected_catalog and design_number:
                    banner_preview = f"{selected_catalog} 6.30 D.No {design_number}"
                    output_name = f"{selected_catalog} - {design_number}.jpg"
                    st.info(
                        f"**Banner Text:** `{banner_preview}`\n"
                        f"**File:** `{output_name}`\n"
                        f"**Folder:** `Shobha Sarees/{selected_catalog}/`"
                    )

    st.divider()
    if st.button("🚀 Process & Upload (Simple)", type="primary", use_container_width=True, key="simple_submit"):
        if not selected_catalog:
            st.error("❌ Please select a catalog!")
        elif not simple_files:
            st.error("❌ Please upload at least one image!")
        else:
            progress_bar = st.progress(0)
            status_placeholder = st.empty()
            results = []

            missing_designs = []
            for idx, _uploaded_file in enumerate(simple_files):
                if not st.session_state["simple_design_numbers"].get(idx):
                    missing_designs.append(f"Image {idx + 1}")
            if missing_designs:
                st.error(f"❌ Please enter design numbers for: {', '.join(missing_designs)}")
            else:
                for idx, uploaded_file in enumerate(simple_files):
                    box = status_placeholder

                    def cb(msg, i=idx, b=box):
                        b.markdown(f"**Image {i + 1}:** {msg}")

                    try:
                        dn = st.session_state["simple_design_numbers"][idx]
                        filename, url = process_and_upload_image(uploaded_file, selected_catalog, dn, cb)
                        box.markdown(f"**Image {idx + 1}:** ✅ Successfully uploaded • [Drive]({url})")
                        results.append({"filename": filename, "catalog": selected_catalog, "url": url, "status": "success"})
                    except Exception as e:
                        box.error(f"**Image {idx + 1}:** ❌ Error: {e}")
                        results.append({"filename": f"Image {idx+1}", "catalog": selected_catalog, "url": None, "status": "error", "error": str(e)})

                    progress_bar.progress((idx + 1) / len(simple_files))

                status_placeholder.empty()

                successful = [r for r in results if r["status"] == "success"]
                failed = [r for r in results if r["status"] == "error"]

                if successful:
                    st.toast("Batch upload complete", icon="✅")
                    st.success(f"✅ Successfully processed {len(successful)} image(s)!")
                    for r in successful:
                        st.success(f"📁 **{r['filename']}** → `Shobha Sarees/{r['catalog']}/` • [Drive]({r['url']})")

                if failed:
                    st.error(f"❌ Failed to process {len(failed)} image(s):")
                    for r in failed:
                        st.error(f"**{r['filename']}** → {r.get('error', 'Unknown error')}")

                if results and all(r["status"] == "success" for r in results):
                    st.balloons()
                    st.session_state["simple_design_numbers"] = {}
                    st.rerun()
