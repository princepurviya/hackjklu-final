"""
app.py - Streamlit dashboard for AI-Powered Exhibit Monitoring (Multi-Camera).

Uses background threads so ALL cameras can stream concurrently.
Clicking "View Alerts" in the sidebar opens a @st.dialog popup modal.

Run with:  streamlit run app.py
"""

import base64
import io
import uuid
import cv2
import time
import threading
import numpy as np
import streamlit as st
from PIL import Image
from datetime import datetime, timedelta, date, time as dtime

from detector import DamageDetector, UNWANTED_CLASSES
from comparator import compare_images
from utils import trigger_alert


# ============================================================================
# CameraThread
# ============================================================================

class CameraThread:
    def __init__(self, source):
        self.source = source
        self.cap = cv2.VideoCapture(source)
        self.frame = None
        self.running = False
        self.lock = threading.Lock()
        self._thread = None

    def start(self):
        if not self.cap.isOpened():
            self.cap = cv2.VideoCapture(self.source)
        if not self.cap.isOpened():
            return False
        self.running = True
        self._thread = threading.Thread(target=self._loop, daemon=True)
        self._thread.start()
        return True

    def _loop(self):
        while self.running:
            ret, frame = self.cap.read()
            if not ret:
                time.sleep(0.05)
                continue
            with self.lock:
                self.frame = frame

    def read(self):
        with self.lock:
            return self.frame.copy() if self.frame is not None else None

    def stop(self):
        self.running = False
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=2)
        if self.cap.isOpened():
            self.cap.release()
        self.frame = None

    def is_opened(self):
        return self.cap.isOpened() and self.running


# ============================================================================
# Helpers
# ============================================================================

def make_camera(name, cam_type, source):
    return {
        "name": name, "type": cam_type, "source": source,
        "baseline": None, "baseline_objects": [],
        "baseline_stabilize_frames": 0,
    }


def detect_misplacement_and_foreign(baseline_objects, current_objects,
                                    movement_threshold=50, min_confidence=0.35):
    baseline_by_label = {}
    for obj in baseline_objects:
        baseline_by_label.setdefault(obj["label"], []).append(obj)

    moved_objects, foreign_objects = [], []
    for current in current_objects:
        if current["confidence"] < min_confidence:
            continue
        candidates = baseline_by_label.get(current["label"], [])
        if not candidates:
            foreign_objects.append(current)
            continue
        cx, cy = current["center"]
        distances = [
            ((cx - b["center"][0]) ** 2 + (cy - b["center"][1]) ** 2) ** 0.5
            for b in candidates
        ]
        if min(distances) > movement_threshold:
            moved = current.copy()
            moved["shift"] = round(min(distances), 1)
            moved_objects.append(moved)
    return moved_objects, foreign_objects


def _build_alert(message, severity="HIGH", category="damage",
                 baseline_img=None, current_img=None, bboxes=None,
                 confidence=0.0, ssim=None):
    st.session_state.alert_counter = st.session_state.get("alert_counter", 0) + 1
    return {
        "alert_id":     str(uuid.uuid4()),
        "alert_type":   category,
        "timestamp":    datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "severity":     severity,
        "category":     category,
        "message":      message,
        "baseline_img": baseline_img.copy() if baseline_img is not None else None,
        "current_img":  current_img.copy()  if current_img  is not None else None,
        "bboxes":       bboxes or [],
        "confidence":   round(float(confidence), 3),
        "ssim":         ssim,
    }


def _push_alerts(new_alerts):
    for a in new_alerts:
        st.session_state.alerts.insert(0, a)
    st.session_state.alerts = st.session_state.alerts[:50]


def process_frame(frame, cam, detector, crack_sensitivity,
                  ssim_threshold, movement_threshold):
    cam_name = cam["name"]
    alerts, bboxes = [], []

    scene_detections = detector.detect_scene_objects(frame)
    detections = [d for d in scene_detections if d["label"] in UNWANTED_CLASSES]
    annotated = detector.draw_object_detections(frame, detections)

    crack_found, crack_count = False, 0
    if cam["baseline"] is None:
        annotated, crack_found, crack_count = detector.detect_cracks(
            annotated, sensitivity=crack_sensitivity,
        )

    ssim_score = None
    moved_objects, foreign_objects = [], []

    if cam["baseline"] is not None:
        if cam["baseline_stabilize_frames"] > 0:
            cam["baseline_stabilize_frames"] -= 1
        else:
            result = compare_images(
                cam["baseline"], frame, ssim_threshold,
                method="absdiff", blur_ksize=21,
                min_change_area=800, diff_threshold=30,
            )
            ssim_score = result["ssim_score"]

            if result["changed_contours"]:
                for cnt in result["changed_contours"]:
                    x, y, w, h = cv2.boundingRect(cnt)
                    bboxes.append((x, y, x + w, y + h))
                    cv2.rectangle(annotated, (x, y), (x+w, y+h), (0, 0, 255), 3)
                    cv2.putText(annotated, "MISPLACED",
                                (x, max(14, y-8)), cv2.FONT_HERSHEY_SIMPLEX,
                                0.6, (0, 0, 255), 2)

            moved_objects, foreign_objects = detect_misplacement_and_foreign(
                cam["baseline_objects"], scene_detections,
                movement_threshold=movement_threshold,
                min_confidence=detector.confidence,
            )

            for m in moved_objects:
                x1, y1, x2, y2 = m["bbox"]
                bboxes.append((x1, y1, x2, y2))
                cv2.rectangle(annotated, (x1, y1), (x2, y2), (255, 165, 0), 2)
                cv2.putText(annotated, f"MOVED {m['label']} ({m['shift']:.0f}px)",
                            (x1, max(14, y1-6)), cv2.FONT_HERSHEY_SIMPLEX,
                            0.5, (255, 165, 0), 2)

            for f in foreign_objects:
                x1, y1, x2, y2 = f["bbox"]
                bboxes.append((x1, y1, x2, y2))
                cv2.rectangle(annotated, (x1, y1), (x2, y2), (0, 255, 0), 2)
                cv2.putText(annotated, f"NEW {f['label']}",
                            (x1, max(14, y1-6)), cv2.FONT_HERSHEY_SIMPLEX,
                            0.5, (0, 255, 0), 2)

            if result["damage_detected"]:
                num = len(result.get("changed_contours", []))
                alerts.append(_build_alert(
                    f"[{cam_name}] Misplaced object - {num} region(s)",
                    severity="HIGH", category="misplaced",
                    baseline_img=cam["baseline"], current_img=frame,
                    bboxes=bboxes, ssim=ssim_score,
                ))

    if detections:
        labels = ", ".join(d["label"] for d in detections)
        alerts.append(_build_alert(
            f"[{cam_name}] Unwanted objects: {labels}", category="foreign",
            baseline_img=cam["baseline"], current_img=frame,
            bboxes=[d["bbox"] for d in detections],
            confidence=max((d["confidence"] for d in detections), default=0),
        ))

    if crack_found:
        alerts.append(_build_alert(
            f"[{cam_name}] Cracks detected ({crack_count} region(s))",
            category="damage", baseline_img=cam["baseline"],
            current_img=frame, bboxes=bboxes,
        ))

    if moved_objects:
        alerts.append(_build_alert(
            f"[{cam_name}] Misplaced: {len(moved_objects)} YOLO object(s)",
            severity="HIGH", category="misplaced",
            baseline_img=cam["baseline"], current_img=frame,
            bboxes=[m["bbox"] for m in moved_objects],
            confidence=max((m["confidence"] for m in moved_objects), default=0),
        ))

    if foreign_objects:
        labels = ", ".join(f["label"] for f in foreign_objects)
        alerts.append(_build_alert(
            f"[{cam_name}] Foreign object: {labels}",
            severity="HIGH", category="foreign",
            baseline_img=cam["baseline"], current_img=frame,
            bboxes=[f["bbox"] for f in foreign_objects],
            confidence=max((f["confidence"] for f in foreign_objects), default=0),
        ))

    return annotated, alerts, {
        "objects": len(detections),
        "cracks":  crack_count if crack_found else 0,
        "ssim":    ssim_score,
    }


def highlight_alert_image(img_bgr, bboxes, label="Detected", color=(0, 0, 255)):
    out = img_bgr.copy()
    for i, bbox in enumerate(bboxes):
        if len(bbox) == 4:
            x1, y1, x2, y2 = [int(v) for v in bbox]
            cv2.rectangle(out, (x1, y1), (x2, y2), color, 2)
            cv2.putText(out, f"{label} #{i+1}", (x1, max(14, y1-6)),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.55, color, 2)
    return cv2.cvtColor(out, cv2.COLOR_BGR2RGB)


def _img_to_b64_thumb(img_bgr, w=80, h=60):
    small = cv2.resize(img_bgr, (w, h))
    buf = io.BytesIO()
    Image.fromarray(cv2.cvtColor(small, cv2.COLOR_BGR2RGB)).save(buf, "JPEG", quality=70)
    return base64.b64encode(buf.getvalue()).decode()


# ============================================================================
# Page config & CSS
# ============================================================================

st.set_page_config(
    page_title="AI-Powered Exhibit Monitoring System",
    layout="wide",
    initial_sidebar_state="expanded",
)

ALERT_TYPE_LABELS = {
    "crack":     ("Crack Detected",      "badge-crack"),
    "damage":    ("Structural Damage",   "badge-damage"),
    "misplaced": ("Misplaced Object",    "badge-misplaced"),
    "foreign":   ("Foreign Object",      "badge-foreign"),
}

st.markdown("""
<style>
body, .main, .stApp { background-color: #000 !important; color: #fff !important; }
* { color: #fff !important; }

.main-header {
    background: #1a1a1a; padding: 1.2rem 2rem;
    border-radius: 12px; margin-bottom: 1.5rem; text-align: center;
}
.main-header h1 { margin: 0; font-size: 1.9rem; letter-spacing: 1px; }
.main-header p  { color: #ccc; margin: .3rem 0 0; font-size: .95rem; }

.metric-card {
    background: #1a1a1a; border: 1px solid #333;
    border-radius: 10px; padding: .7rem; text-align: center; margin-bottom: .5rem;
}
.metric-card h3 { margin: 0; font-size: .75rem; text-transform: uppercase; }
.metric-card .value { font-size: 1.4rem; font-weight: 700; }

.alert-box {
    background: #2a0000; border-left: 4px solid #ef4444;
    border-radius: 6px; padding: .6rem .8rem; margin-bottom: .5rem; font-size: .82rem;
}
.alert-box .ts { color: #aaa; font-size: .7rem; }
.safe-box {
    background: #002a00; border-left: 4px solid #22c55e;
    border-radius: 6px; padding: .8rem 1rem; font-size: .9rem;
}

.cam-card {
    background: #1a1a1a; border: 1px solid #333;
    border-radius: 8px; padding: .6rem .8rem; margin-bottom: .4rem;
}
.cam-card .cam-name { font-weight: 600; font-size: .9rem; }
.cam-card .cam-type { color: #aaa; font-size: .75rem; }

.stButton>button, .stDownloadButton>button {
    background: linear-gradient(135deg, #e67e22, #ffb347);
    color: #000 !important; border: 1px solid rgba(255,255,255,.15);
    border-radius: 10px; padding: .55rem 1rem; font-weight: 600;
    box-shadow: 0 8px 18px rgba(0,0,0,.25);
    transition: transform .12s ease, box-shadow .12s ease;
}
.stButton>button:hover  { transform: translateY(-1px); box-shadow: 0 12px 20px rgba(0,0,0,.35); }
.stButton>button:active { transform: translateY(0);    box-shadow: 0 6px 14px rgba(0,0,0,.25); }

.stDeployButton, [data-testid="stAppDeployButton"] { display: none; }
#MainMenu, footer { visibility: hidden; }

.stTextInput>label, .stSelectbox>label, .stMultiSelect>label,
.stSlider>label, .stCheckbox>label { color: #fff !important; }
h1,h2,h3,h4,h5,h6 { color: #fff !important; }

[data-testid="stSidebar"] { background-color: #0a0a0a !important; }
[data-testid="stSidebar"] .streamlit-expanderHeader {
    background-color: #1a1a1a !important; border: 1.5px solid #444 !important;
    border-radius: 10px !important; padding: 12px 16px !important;
    margin: 8px 0 !important; transition: all .2s ease !important;
}
[data-testid="stSidebar"] .streamlit-expanderHeader:hover {
    background: linear-gradient(135deg, #e67e22, #ffb347) !important;
    border-color: #e67e22 !important;
}
[data-testid="stSidebar"] .streamlit-expanderHeader p {
    color:#fff !important; font-weight:600 !important;
    font-size:1rem !important; margin:0 !important;
}
[data-testid="stSidebar"] .streamlit-expanderHeader:hover p { color:#000 !important; }
[data-testid="stSidebar"] .streamlit-expanderHeader svg { stroke:#fff !important; stroke-width:2px !important; }
[data-testid="stSidebar"] .streamlit-expanderHeader:hover svg { stroke:#000 !important; }
[data-testid="stSidebar"] hr { border-color:#333 !important; margin:1.2rem 0 !important; }

/* Alert popup dialog styling */
[data-testid="stDialog"] > div {
    background: #111 !important;
    border: 1px solid #2a2a2a !important;
    border-radius: 18px !important;
    box-shadow: 0 30px 80px rgba(0,0,0,.85) !important;
    max-width: 1200px !important;
    width: 95vw !important;
}

/* Alert cards */
.alert-scroll-area { max-height: 50vh; overflow-y: auto; padding-right: 4px; }
.alert-scroll-area::-webkit-scrollbar { width: 5px; }
.alert-scroll-area::-webkit-scrollbar-track { background: #1a1a1a; border-radius: 4px; }
.alert-scroll-area::-webkit-scrollbar-thumb { background: #444; border-radius: 4px; }

/* alert card buttons */
.alert-btn-row { margin-bottom: 6px; }
.alert-btn-row > div > button {
    background: #1a1a1a !important;
    border: 1px solid #2f2f2f !important;
    border-radius: 10px !important;
    padding: 10px 12px !important;
    text-align: left !important;
    color: #fff !important;
    width: 100% !important;
    font-size: .82rem !important;
    transition: border-color .15s, background .15s !important;
}
.alert-btn-row > div > button:hover {
    border-color: #e67e22 !important;
    background: #231a10 !important;
    transform: none !important;
}
.alert-btn-row.active-card > div > button {
    border-color: #e67e22 !important;
    background: #231a10 !important;
}

/* Detail badges */
.detail-badge {
    display: inline-block; padding: 3px 14px; border-radius: 20px;
    font-size: .75rem; font-weight: 700; letter-spacing: .05em; margin-bottom: .8rem;
}
.badge-crack     { background: #7f1d1d; color: #fca5a5; }
.badge-misplaced { background: #78350f; color: #fcd34d; }
.badge-foreign   { background: #1e3a5f; color: #93c5fd; }
.badge-damage    { background: #3b0764; color: #d8b4fe; }

/* Sidebar alert button */
.view-alerts-btn > div > button {
    background: linear-gradient(135deg, #c0392b, #e74c3c) !important;
    color: #fff !important; font-size: 1rem !important;
    padding: .65rem 1.2rem !important; border-radius: 12px !important;
    border: none !important; width: 100% !important;
    box-shadow: 0 6px 20px rgba(192,57,43,.4) !important;
}
.view-alerts-btn > div > button:hover {
    transform: translateY(-2px) !important;
    box-shadow: 0 10px 28px rgba(192,57,43,.6) !important;
}
</style>
""", unsafe_allow_html=True)

st.markdown("""
<div class="main-header">
    <h1>AI-Powered Exhibit Monitoring System</h1>
    <p>Multi-camera real-time detection of misplaced objects and structural damage</p>
</div>
""", unsafe_allow_html=True)


# ============================================================================
# Session state
# ============================================================================

_defaults = {
    "detector":          DamageDetector(),
    "cameras":           [make_camera("Camera 1", "Laptop Webcam", 0)],
    "cam_threads":       {},
    "all_running":       False,
    "alerts":            [],
    "alert_counter":     0,
    "selected_alert_id": None,
    "selected_alert":    None,   # full alert dict for Alert Preview tab
    "crack_sensitivity":  "High",
    "ssim_threshold":     0.85,
    "movement_threshold": 50,
}
for k, v in _defaults.items():
    if k not in st.session_state:
        st.session_state[k] = v

detector = st.session_state.detector


# ============================================================================
# Alert Preview Dashboard — render functions
# ============================================================================

def render_alert_list(alerts: list) -> None:
    """Render a scrollable, clickable alert list (LEFT panel, 30%)."""

    st.markdown(
        '<h4 style="margin:0 0 .6rem 0;">Alerts</h4>',
        unsafe_allow_html=True,
    )

    if not alerts:
        st.info("No alerts recorded yet. Start a camera feed to begin monitoring.")
        return

    col_h1, col_h2 = st.columns([3, 1])
    col_h1.markdown(f"**{len(alerts)} alert(s)**")
    if col_h2.button("Clear All", key="ap_clear_all", use_container_width=True):
        st.session_state.alerts = []
        st.session_state.selected_alert_id = None
        st.session_state.selected_alert = None
        st.rerun()

    # Scrollable container
    st.markdown(
        '<div class="alert-scroll-area" style="max-height:74vh;">',
        unsafe_allow_html=True,
    )

    for i, a in enumerate(alerts):
        atype    = a.get("alert_type", a.get("category", "damage"))
        label, badge_cls = ALERT_TYPE_LABELS.get(atype, ("Alert", "badge-damage"))
        ts_str   = a.get("timestamp", "")
        aid      = a.get("alert_id", "")
        msg_short = a.get("message", "")[:60]
        cam_name  = msg_short.split("]")[0].lstrip("[") if "]" in msg_short else "—"
        is_active = aid == st.session_state.selected_alert_id

        active_cls = "active-card" if is_active else ""
        st.markdown(f'<div class="alert-btn-row {active_cls}">', unsafe_allow_html=True)
        if st.button(
            f"{label}  |  {ts_str}\n{msg_short}",
            key=f"ap_btn_{i}_{aid[:8]}",
            use_container_width=True,
        ):
            st.session_state.selected_alert_id = aid
            st.session_state.selected_alert = a
            st.rerun()
        st.markdown("</div>", unsafe_allow_html=True)

    st.markdown("</div>", unsafe_allow_html=True)


def render_alert_details() -> None:
    """Render alert info + side-by-side Baseline vs Detected comparison (RIGHT panel, 70%)."""

    # ── Resolve selected alert ──────────────────────────────────────────
    sel = st.session_state.get("selected_alert")
    if sel is None and st.session_state.get("selected_alert_id"):
        aid = st.session_state.selected_alert_id
        sel = next((a for a in st.session_state.alerts if a.get("alert_id") == aid), None)
        if sel:
            st.session_state.selected_alert = sel

    if sel is None:
        st.markdown(
            '<div style="display:flex;align-items:center;justify-content:center;'
            'height:60vh;color:#555;font-size:1.15rem;">'
            'Select an alert from the list to view the baseline vs detected comparison.'
            '</div>',
            unsafe_allow_html=True,
        )
        return

    # ── Alert metadata ──────────────────────────────────────────────────
    atype      = sel.get("alert_type", sel.get("category", "damage"))
    label, badge_cls = ALERT_TYPE_LABELS.get(atype, ("Alert", "badge-damage"))
    ts_str     = sel.get("timestamp", "")
    severity   = sel.get("severity", "HIGH")
    conf       = sel.get("confidence", 0)
    ssim_v     = sel.get("ssim")
    msg        = sel.get("message", "")
    bboxes     = sel.get("bboxes", [])

    # Extract camera name from message if available
    camera_id = msg.split("]")[0].lstrip("[") if "]" in msg else "—"

    # Type badge
    st.markdown(
        f'<span class="detail-badge {badge_cls}">{label.upper()}</span>',
        unsafe_allow_html=True,
    )

    # Info cards row
    mi1, mi2, mi3, mi4 = st.columns(4)
    mi1.markdown(
        f'<div class="metric-card"><h3>Camera</h3>'
        f'<div class="value" style="font-size:.95rem;">{camera_id}</div></div>',
        unsafe_allow_html=True)
    mi2.markdown(
        f'<div class="metric-card"><h3>Timestamp</h3>'
        f'<div class="value" style="font-size:.85rem;">{ts_str}</div></div>',
        unsafe_allow_html=True)
    mi3.markdown(
        f'<div class="metric-card"><h3>Alert Type</h3>'
        f'<div class="value" style="font-size:.95rem;">{label}</div></div>',
        unsafe_allow_html=True)
    ssim_disp = f"{ssim_v:.2%}" if ssim_v is not None else "N/A"
    mi4.markdown(
        f'<div class="metric-card"><h3>Confidence</h3>'
        f'<div class="value" style="font-size:.95rem;">{conf:.0%}</div></div>',
        unsafe_allow_html=True)

    st.markdown(f"**Details:** {msg}")
    st.markdown("---")

    # ── Side-by-side image comparison ───────────────────────────────────
    baseline_arr = sel.get("baseline_img")
    current_arr  = sel.get("current_img")
    has_base = baseline_arr is not None
    has_curr = current_arr  is not None

    if has_base or has_curr:
        col1, col2 = st.columns(2)

        with col1:
            st.markdown(
                '<h5 style="text-align:center;margin-bottom:.3rem;">'
                'Baseline Reference</h5>',
                unsafe_allow_html=True,
            )
            if has_base:
                st.image(
                    cv2.cvtColor(baseline_arr, cv2.COLOR_BGR2RGB),
                    use_container_width=True,
                    caption="Baseline — captured during setup",
                )
            else:
                st.info("No baseline image captured for this alert.")

        with col2:
            st.markdown(
                '<h5 style="text-align:center;margin-bottom:.3rem;">'
                'Detected Anomaly</h5>',
                unsafe_allow_html=True,
            )
            if has_curr:
                # Draw YOLO bounding boxes in red with the anomaly type label
                type_labels = {
                    "crack":     "CRACK",
                    "misplaced": "MISPLACED OBJECT",
                    "foreign":   "FOREIGN OBJECT",
                    "damage":    "DAMAGE",
                }
                annotation_label = type_labels.get(atype, label.upper())

                if bboxes:
                    annotated = highlight_alert_image(
                        current_arr, bboxes,
                        label=annotation_label,
                        color=(0, 0, 255),  # red in BGR
                    )
                    st.image(
                        annotated,
                        use_container_width=True,
                        caption=f"Detected: {annotation_label}",
                    )
                else:
                    st.image(
                        cv2.cvtColor(current_arr, cv2.COLOR_BGR2RGB),
                        use_container_width=True,
                        caption="Current frame (no bounding boxes)",
                    )
            else:
                st.info("No current image available for this alert.")

        # ── Difference heatmap (collapsible) ────────────────────────────
        if has_base and has_curr and baseline_arr.shape == current_arr.shape:
            with st.expander("Show Difference Heatmap"):
                try:
                    diff_result = compare_images(
                        baseline_arr, current_arr, 0.85,
                        method="absdiff", blur_ksize=21,
                        min_change_area=800, diff_threshold=30,
                    )
                    st.image(
                        cv2.cvtColor(diff_result["diff_image"], cv2.COLOR_BGR2RGB),
                        caption="Difference Heatmap",
                        use_container_width=True,
                    )
                    score = diff_result["ssim_score"]
                    (st.error if diff_result["damage_detected"] else st.success)(
                        f"{'Change detected' if diff_result['damage_detected'] else 'Stable'} "
                        f"— SSIM: {score:.2%}"
                    )
                except Exception as e:
                    st.warning(f"Could not compute diff: {e}")
    else:
        st.info("No images captured for this alert.")




# ============================================================================
# Sidebar
# ============================================================================

with st.sidebar:
    st.markdown(
        '<a href="http://localhost:5173" '
        'style="font-size:1.15rem;font-weight:700;color:#fff;'
        'padding:.4rem 0 .2rem;letter-spacing:.5px;'
        'text-decoration:none;display:block;cursor:pointer;">'
        'AI-Powered Monitoring</a>',
        unsafe_allow_html=True,
    )
    st.divider()



    # Alert stat pills
    if st.session_state.alerts:
        total     = len(st.session_state.alerts)
        cracks    = sum(1 for a in st.session_state.alerts if a.get("alert_type") == "crack")
        misplaced = sum(1 for a in st.session_state.alerts if a.get("alert_type") == "misplaced")
        foreign   = sum(1 for a in st.session_state.alerts if a.get("alert_type") == "foreign")
        st.markdown(
            f'<div style="display:flex;gap:6px;flex-wrap:wrap;margin-top:8px;">'
            f'<span style="background:#333;padding:2px 10px;border-radius:20px;font-size:.75rem;">Total {total}</span>'
            f'<span style="background:#7f1d1d;padding:2px 10px;border-radius:20px;font-size:.75rem;">Crack {cracks}</span>'
            f'<span style="background:#78350f;padding:2px 10px;border-radius:20px;font-size:.75rem;">Moved {misplaced}</span>'
            f'<span style="background:#1e3a5f;padding:2px 10px;border-radius:20px;font-size:.75rem;">Foreign {foreign}</span>'
            f'</div>',
            unsafe_allow_html=True,
        )

    st.divider()

    # Controls expander
    with st.expander("Controls", expanded=True):
        with st.expander("Add Camera", expanded=False):
            new_name = st.text_input("Camera Name",
                                      value=f"Camera {len(st.session_state.cameras)+1}",
                                      key="new_cam_name")
            new_type = st.radio("Camera Type", ["Laptop Webcam", "IP Webcam"], key="new_cam_type")
            if new_type == "Laptop Webcam":
                new_source = int(st.number_input("Camera index", 0, 10, 0, key="new_cam_idx"))
            else:
                new_source = st.text_input("IP Webcam URL",
                                            value="http://192.168.1.5:8080/video",
                                            key="new_cam_url")
            if st.button("Add Camera", key="add_cam_btn", use_container_width=True):
                st.session_state.cameras.append(make_camera(new_name, new_type, new_source))
                st.success(f"Added: {new_name}")
                st.rerun()

    # Cameras expander
    with st.expander("Cameras", expanded=True):
        for i, cam in enumerate(st.session_state.cameras):
            running = (cam["name"] in st.session_state.cam_threads
                       and st.session_state.cam_threads[cam["name"]].running)
            status = "Live" if running else "Stopped"
            bl = "Baseline set" if cam["baseline"] is not None else "No baseline"
            st.markdown(
                f'<div class="cam-card">'
                f'<span class="cam-name">{cam["name"]} - {status}</span><br>'
                f'<span class="cam-type">{cam["type"]} | {bl}</span>'
                f'</div>', unsafe_allow_html=True,
            )
            bc1, bc2 = st.columns(2)
            with bc1:
                if st.button("Remove", key=f"rm_{i}", use_container_width=True):
                    t = st.session_state.cam_threads.pop(cam["name"], None)
                    if t: t.stop()
                    st.session_state.cameras.pop(i)
                    st.rerun()
            with bc2:
                if cam["baseline"] is not None:
                    if st.button("Clear BL", key=f"clear_bl_{i}", use_container_width=True):
                        cam["baseline"] = None
                        cam["baseline_objects"] = []
                        st.rerun()

        if not st.session_state.cameras:
            st.info("No cameras yet. Add one above.")

    # Detection settings
    with st.expander("Detection Settings", expanded=False):
        confidence = st.slider("YOLO Confidence", 0.1, 1.0, 0.40, 0.05)
        detector.confidence = confidence
        st.session_state.crack_sensitivity  = st.select_slider(
            "Crack Sensitivity", options=["Low", "Medium", "High"],
            value=st.session_state.crack_sensitivity)
        st.session_state.ssim_threshold     = st.slider(
            "Baseline Match Threshold", 0.50, 1.0, st.session_state.ssim_threshold, 0.05)
        st.session_state.movement_threshold = st.slider(
            "Movement Threshold (px)", 20, 200, st.session_state.movement_threshold, 5)

crack_sensitivity  = st.session_state.crack_sensitivity
ssim_threshold     = st.session_state.ssim_threshold
movement_threshold = st.session_state.movement_threshold


# ============================================================================
# Main: monitoring tabs (always visible)
# ============================================================================

tab_camera, tab_alerts, tab_upload, tab_compare = st.tabs([
    "Live Cameras", "Alert Preview", "Upload Image", "Before / After"
])

# TAB 2 - Alert Preview Dashboard
with tab_alerts:
    # ── Filter bar ──────────────────────────────────────────────────────
    flt_c1, flt_c2 = st.columns([1, 3])
    with flt_c1:
        ap_type_filter = st.selectbox(
            "Filter by Type",
            ["All", "Crack / Damage", "Misplaced Object", "Foreign Object"],
            key="ap_type_filter",
        )

    _ap_type_map = {
        "Crack / Damage": ("crack", "damage"),
        "Misplaced Object": ("misplaced",),
        "Foreign Object": ("foreign",),
    }

    all_alerts = st.session_state.alerts
    if ap_type_filter == "All":
        filtered_alerts = all_alerts
    else:
        allowed = _ap_type_map.get(ap_type_filter, ())
        filtered_alerts = [
            a for a in all_alerts
            if a.get("alert_type", a.get("category", "")) in allowed
        ]

    with flt_c2:
        st.markdown(
            f'<p style="margin-top:1.8rem;color:#aaa;font-size:.85rem;">'
            f'Showing <b style="color:#fff;">{len(filtered_alerts)}</b> of '
            f'<b style="color:#fff;">{len(all_alerts)}</b> total alerts</p>',
            unsafe_allow_html=True,
        )

    st.markdown("---")

    # ── Two-column layout: list (30%) | detail (70%) ────────────────────
    left_col, right_col = st.columns([1, 2], gap="medium")

    # ── LEFT: alert list ────────────────────────────────────────────────
    with left_col:
        st.markdown('<h4 style="margin:0 0 .5rem 0;">Alerts</h4>', unsafe_allow_html=True)

        if not filtered_alerts:
            if not all_alerts:
                st.info("No alerts recorded yet. Start a camera feed to begin monitoring.")
            else:
                st.warning("No alerts match the current filter.")
        else:
            hdr1, hdr2 = st.columns([3, 1])
            hdr1.markdown(f"**{len(filtered_alerts)} alert(s)**")
            if hdr2.button("Clear All", key="ap_clear_btn", use_container_width=True):
                st.session_state.alerts = []
                st.session_state.selected_alert_id = None
                st.session_state.selected_alert = None
                st.rerun()

            for idx, alert in enumerate(filtered_alerts):
                a_type  = alert.get("alert_type", alert.get("category", "damage"))
                a_label, a_badge = ALERT_TYPE_LABELS.get(a_type, ("Alert", "badge-damage"))
                a_ts    = alert.get("timestamp", "")
                a_id    = alert.get("alert_id", "")
                a_msg   = alert.get("message", "")[:60]
                is_sel  = (a_id == st.session_state.get("selected_alert_id"))

                active_cls = "active-card" if is_sel else ""
                st.markdown(
                    f'<div class="alert-btn-row {active_cls}">',
                    unsafe_allow_html=True,
                )
                if st.button(
                    f"{a_label}  •  {a_ts}\n{a_msg}",
                    key=f"ap_alert_{idx}_{a_id[:8]}",
                    use_container_width=True,
                ):
                    st.session_state.selected_alert_id = a_id
                    st.session_state.selected_alert = alert
                    st.rerun()
                st.markdown("</div>", unsafe_allow_html=True)

    # ── RIGHT: detail viewer ────────────────────────────────────────────
    with right_col:
        # Resolve selected alert
        sel = st.session_state.get("selected_alert")
        if sel is None and st.session_state.get("selected_alert_id"):
            sel = next(
                (a for a in all_alerts if a.get("alert_id") == st.session_state.selected_alert_id),
                None,
            )
            if sel:
                st.session_state.selected_alert = sel

        if sel is None:
            st.markdown(
                '<div style="display:flex;align-items:center;justify-content:center;'
                'height:55vh;color:#555;font-size:1.1rem;">'
                'Select an alert from the list to view the baseline vs detected comparison.'
                '</div>',
                unsafe_allow_html=True,
            )
        else:
            # ── Alert info ──────────────────────────────────────────────
            a_type = sel.get("alert_type", sel.get("category", "damage"))
            lbl, badge_cls = ALERT_TYPE_LABELS.get(a_type, ("Alert", "badge-damage"))
            ts     = sel.get("timestamp", "")
            sev    = sel.get("severity", "HIGH")
            conf   = sel.get("confidence", 0)
            msg    = sel.get("message", "")
            bboxes = sel.get("bboxes", [])
            cam_id = msg.split("]")[0].lstrip("[") if "]" in msg else "—"

            st.markdown(
                f'<span class="detail-badge {badge_cls}">{lbl.upper()}</span>',
                unsafe_allow_html=True,
            )

            m1, m2, m3, m4 = st.columns(4)
            m1.markdown(
                f'<div class="metric-card"><h3>Camera</h3>'
                f'<div class="value" style="font-size:.9rem;">{cam_id}</div></div>',
                unsafe_allow_html=True)
            m2.markdown(
                f'<div class="metric-card"><h3>Timestamp</h3>'
                f'<div class="value" style="font-size:.8rem;">{ts}</div></div>',
                unsafe_allow_html=True)
            m3.markdown(
                f'<div class="metric-card"><h3>Alert Type</h3>'
                f'<div class="value" style="font-size:.9rem;">{lbl}</div></div>',
                unsafe_allow_html=True)
            m4.markdown(
                f'<div class="metric-card"><h3>Confidence</h3>'
                f'<div class="value" style="font-size:.9rem;">{conf:.0%}</div></div>',
                unsafe_allow_html=True)

            st.markdown(f"**Details:** {msg}")
            st.markdown("---")

            # ── Side-by-side: Baseline vs Detected ──────────────────────
            baseline_arr = sel.get("baseline_img")
            current_arr  = sel.get("current_img")
            has_base = baseline_arr is not None
            has_curr = current_arr  is not None

            if has_base or has_curr:
                img_c1, img_c2 = st.columns(2)

                with img_c1:
                    st.markdown("##### Baseline Reference")
                    if has_base:
                        st.image(
                            cv2.cvtColor(baseline_arr, cv2.COLOR_BGR2RGB),
                            use_container_width=True,
                            caption="Baseline — captured during setup",
                        )
                    else:
                        st.info("No baseline image captured.")

                with img_c2:
                    st.markdown("##### Detected Anomaly")
                    if has_curr:
                        type_labels = {
                            "crack": "CRACK", "misplaced": "MISPLACED OBJECT",
                            "foreign": "FOREIGN OBJECT", "damage": "DAMAGE",
                        }
                        anno_label = type_labels.get(a_type, lbl.upper())

                        if bboxes:
                            annotated = highlight_alert_image(
                                current_arr, bboxes,
                                label=anno_label, color=(0, 0, 255),
                            )
                            st.image(annotated, use_container_width=True,
                                     caption=f"Detected: {anno_label}")
                        else:
                            st.image(
                                cv2.cvtColor(current_arr, cv2.COLOR_BGR2RGB),
                                use_container_width=True,
                                caption="Current frame (no bounding boxes)",
                            )
                    else:
                        st.info("No current image available.")

                # Difference heatmap
                if has_base and has_curr and baseline_arr.shape == current_arr.shape:
                    with st.expander("Show Difference Heatmap"):
                        try:
                            diff_result = compare_images(
                                baseline_arr, current_arr, 0.85,
                                method="absdiff", blur_ksize=21,
                                min_change_area=800, diff_threshold=30,
                            )
                            st.image(
                                cv2.cvtColor(diff_result["diff_image"], cv2.COLOR_BGR2RGB),
                                caption="Difference Heatmap",
                                use_container_width=True,
                            )
                            score = diff_result["ssim_score"]
                            (st.error if diff_result["damage_detected"] else st.success)(
                                f"{'Change detected' if diff_result['damage_detected'] else 'Stable'} "
                                f"— SSIM: {score:.2%}"
                            )
                        except Exception as e:
                            st.warning(f"Could not compute diff: {e}")
            else:
                st.info("No images captured for this alert.")

# TAB 1 - Live cameras
with tab_camera:
    if not st.session_state.cameras:
        st.warning("No cameras configured. Add one from the sidebar.")
    else:
        bc1, bc2, bc3 = st.columns(3)
        with bc1: start_all   = st.button("Start All Cameras",      key="start_all",   use_container_width=True)
        with bc2: stop_all    = st.button("Stop All Cameras",        key="stop_all",    use_container_width=True)
        with bc3: capture_all = st.button("Capture Baseline (All)", key="capture_all", use_container_width=True)

        main_col, alert_col = st.columns([3, 2])
        with alert_col:
            st.subheader("Live Alerts")
            dmg_col, mis_col, for_col = st.columns(3)
            dmg_ph = dmg_col.empty()
            mis_ph = mis_col.empty()
            for_ph = for_col.empty()

        # ── Handle button actions (state changes only) ──────────────────
        if stop_all:
            st.session_state.all_running = False
            for name, t in st.session_state.cam_threads.items():
                t.stop()
            st.session_state.cam_threads = {}
            st.success("All cameras stopped.")

        if capture_all:
            captured = 0
            for cam in st.session_state.cameras:
                t = st.session_state.cam_threads.get(cam["name"])
                if t and t.running:
                    frame = t.read()
                    if frame is not None:
                        cam["baseline"] = frame.copy()
                        cam["baseline_objects"] = detector.detect_scene_objects(frame)
                        cam["baseline_stabilize_frames"] = 5
                        captured += 1
            if captured:
                st.success(f"Baselines captured for {captured} camera(s)!")
            else:
                st.warning("No active camera to capture baseline from.")

        if start_all:
            for cam in st.session_state.cameras:
                name = cam["name"]
                if name not in st.session_state.cam_threads or not st.session_state.cam_threads[name].running:
                    t = CameraThread(cam["source"])
                    if t.start():
                        st.session_state.cam_threads[name] = t
                    else:
                        st.error(f"Cannot open {name} ({cam['source']})")
            st.session_state.all_running = True

        # ── Always re-render and loop when cameras are running ───────────
        # This block re-enters on every Streamlit script rerun so the
        # feed stays alive while the user navigates sidebar sections or
        # opens the Alerts popup.
        if st.session_state.all_running:
            with main_col:
                num_cams = len(st.session_state.cameras)
                cols_per_row = 2 if num_cams > 1 else 1
                placeholders, metric_placeholders = {}, {}
                rows_needed = (num_cams + cols_per_row - 1) // cols_per_row
                cam_idx = 0
                for _ in range(rows_needed):
                    cols = st.columns(cols_per_row)
                    for col in cols:
                        if cam_idx < num_cams:
                            cam = st.session_state.cameras[cam_idx]
                            with col:
                                st.markdown(f"**{cam['name']}**")
                                placeholders[cam["name"]] = st.empty()
                                mc1, mc2, mc3 = st.columns(3)
                                metric_placeholders[f"{cam['name']}_obj"]   = mc1.empty()
                                metric_placeholders[f"{cam['name']}_crack"] = mc2.empty()
                                metric_placeholders[f"{cam['name']}_ssim"]  = mc3.empty()
                            cam_idx += 1

            while st.session_state.all_running:
                any_active = False
                for cam in st.session_state.cameras:
                    name = cam["name"]
                    t = st.session_state.cam_threads.get(name)
                    if not t or not t.running:
                        continue
                    frame = t.read()
                    if frame is None:
                        continue
                    any_active = True

                    annotated, new_alerts, metrics = process_frame(
                        frame, cam, detector,
                        crack_sensitivity, ssim_threshold, movement_threshold,
                    )
                    _push_alerts(new_alerts)

                    if name in placeholders:
                        placeholders[name].image(
                            cv2.cvtColor(annotated, cv2.COLOR_BGR2RGB),
                            channels="RGB", use_container_width=True,
                        )

                    def _mc(key, lbl, val):
                        if key in metric_placeholders:
                            metric_placeholders[key].markdown(
                                f'<div class="metric-card"><h3>{lbl}</h3>'
                                f'<div class="value">{val}</div></div>',
                                unsafe_allow_html=True,
                            )
                    _mc(f"{name}_obj",   "Objects", metrics["objects"])
                    _mc(f"{name}_crack", "Cracks",  metrics["cracks"])
                    _mc(f"{name}_ssim",  "SSIM",
                        f'{metrics["ssim"]:.2%}' if metrics["ssim"] else "N/A")

                now = datetime.now()
                st.session_state.alerts = [
                    a for a in st.session_state.alerts
                    if now - datetime.strptime(a["timestamp"], "%Y-%m-%d %H:%M:%S") < timedelta(minutes=60)
                ]

                dmg_al, mis_al, for_al = [], [], []
                for a in st.session_state.alerts[:15]:
                    cat = a.get("category", "damage")
                    if cat == "misplaced":   mis_al.append(a)
                    elif cat == "foreign":   for_al.append(a)
                    else:                    dmg_al.append(a)

                def _grp(title, items):
                    if not items:
                        return f'<div class="safe-box">No {title.lower()} alerts</div>'
                    h = f'<h4 style="margin:0;padding:.2rem 0;">{title}</h4>'
                    for a in items:
                        h += (f'<div class="alert-box">'
                              f'<span class="ts">{a["timestamp"]}</span><br>{a["message"]}</div>')
                    return h

                dmg_ph.markdown(_grp("Damage",    dmg_al), unsafe_allow_html=True)
                mis_ph.markdown(_grp("Misplaced", mis_al), unsafe_allow_html=True)
                for_ph.markdown(_grp("Foreign",   for_al), unsafe_allow_html=True)

                if not any_active:
                    break
                time.sleep(0.15)
        else:
            with main_col:
                st.info("Click **Start All Cameras** to begin live monitoring.")

# TAB 2 - Upload Image
with tab_upload:
    st.subheader("Upload an Image for Detection")
    uploaded_img = st.file_uploader("Choose an image", type=["png", "jpg", "jpeg"],
                                    key="upload_detect")
    if uploaded_img:
        file_bytes = np.asarray(bytearray(uploaded_img.read()), dtype=np.uint8)
        img = cv2.imdecode(file_bytes, cv2.IMREAD_COLOR)

        c1, c2 = st.columns(2)
        with c1:
            st.image(cv2.cvtColor(img, cv2.COLOR_BGR2RGB),
                     caption="Original Image", use_container_width=True)

        annotated, detections = detector.detect_objects(img)
        annotated, crack_found, crack_count = detector.detect_cracks(
            annotated, sensitivity=crack_sensitivity)

        with c2:
            st.image(cv2.cvtColor(annotated, cv2.COLOR_BGR2RGB),
                     caption="Detection Results", use_container_width=True)

        if detections or crack_found:
            st.error("Damage / Anomaly Detected!")
            if detections:
                st.write("**Unwanted Objects:**")
                for d in detections:
                    st.write(f"- **{d['label']}** - confidence {d['confidence']:.0%}")
            if crack_found:
                st.write(f"**Possible Cracks:** {crack_count} region(s)")
            _push_alerts([_build_alert(
                "Uploaded image - anomaly detected",
                category="crack" if crack_found else "foreign",
                current_img=img,
                bboxes=[d["bbox"] for d in detections],
                confidence=max((d["confidence"] for d in detections), default=0),
            )])
        else:
            st.success("No damage or unwanted objects detected.")

# TAB 3 - Before / After
with tab_compare:
    st.subheader("Before / After Comparison")
    cam_names = [c["name"] for c in st.session_state.cameras]
    if cam_names:
        compare_cam_idx = st.selectbox("Baseline from camera:", range(len(cam_names)),
                                        format_func=lambda i: cam_names[i], key="compare_cam")
        compare_cam = st.session_state.cameras[compare_cam_idx]
    else:
        compare_cam = None

    cb1, cb2 = st.columns(2)
    with cb1:
        st.write("**Baseline (Before)**")
        bl_up = st.file_uploader("Upload baseline", type=["png", "jpg", "jpeg"], key="bl_upload")
        if bl_up:
            baseline_img = cv2.imdecode(np.asarray(bytearray(bl_up.read()), dtype=np.uint8),
                                         cv2.IMREAD_COLOR)
        elif compare_cam and compare_cam["baseline"] is not None:
            baseline_img = compare_cam["baseline"]
        else:
            baseline_img = None

        if baseline_img is not None:
            st.image(cv2.cvtColor(baseline_img, cv2.COLOR_BGR2RGB),
                     caption="Baseline", use_container_width=True)
            if st.button("Remove baseline", key="remove_baseline"):
                if compare_cam:
                    compare_cam["baseline"] = None
                    compare_cam["baseline_objects"] = []
                st.rerun()
        else:
            st.info("Upload or capture a baseline first.")

    with cb2:
        st.write("**Current (After)**")
        curr_up = st.file_uploader("Upload current image",
                                    type=["png", "jpg", "jpeg"], key="curr_upload")
        if curr_up:
            current_img = cv2.imdecode(np.asarray(bytearray(curr_up.read()), dtype=np.uint8),
                                        cv2.IMREAD_COLOR)
            st.image(cv2.cvtColor(current_img, cv2.COLOR_BGR2RGB),
                     caption="Current", use_container_width=True)
        else:
            current_img = None
            st.info("Upload a current image to compare.")

    if baseline_img is not None and current_img is not None:
        st.markdown("---")
        result = compare_images(
            baseline_img, current_img, ssim_threshold,
            method="absdiff", blur_ksize=21, min_change_area=800, diff_threshold=30,
        )
        cd1, cd2 = st.columns([3, 1])
        with cd1:
            st.image(cv2.cvtColor(result["diff_image"], cv2.COLOR_BGR2RGB),
                     caption="Difference Heatmap", use_container_width=True)
        with cd2:
            score = result["ssim_score"]
            st.markdown(
                f'<div class="metric-card"><h3>SSIM Score</h3>'
                f'<div class="value">{score:.2%}</div></div>',
                unsafe_allow_html=True,
            )
            (st.error if result["damage_detected"] else st.success)(
                f"{'Change detected' if result['damage_detected'] else 'Stable'} - SSIM {score:.2%}"
            )
