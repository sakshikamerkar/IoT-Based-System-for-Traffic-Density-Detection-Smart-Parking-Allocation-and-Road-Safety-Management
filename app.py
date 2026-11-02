import streamlit as st
import folium
from streamlit_folium import st_folium
from datetime import datetime
from pathlib import Path
import database as db

st.set_page_config(page_title="SmartCity", page_icon="🚦", layout="wide")
db.init_db()

# ---------- DESIGN ----------
st.markdown("""
<style>
.stApp {background:#F3F6FB}
[data-testid="stSidebar"] {background:#14274E}
[data-testid="stSidebar"] * {color:white}
.block-container {padding-top:2rem}
.hero {background:linear-gradient(120deg,#14274E,#2878B5);
padding:25px;border-radius:16px;color:white;margin-bottom:20px}
.hero h1 {color:white}
div[data-testid="stMetric"] {background:white;padding:15px;
border-radius:12px;border:1px solid #DDE5F0}
</style>
""", unsafe_allow_html=True)

# ---------- SESSION DEFAULTS ----------
for key, value in {"occupied": 4, "vehicles": 20}.items():
    if key not in st.session_state:
        st.session_state[key] = value

TOTAL = 10

def hero(title, subtitle):
    st.markdown(
        f'<div class="hero"><h1>{title}</h1><p>{subtitle}</p></div>',
        unsafe_allow_html=True
    )

def traffic(count):
    if count < 20:
        return "Low", 15, "green"
    if count < 50:
        return "Medium", 30, "orange"
    return "High", 45, "red"
def update_vehicles():
    st.session_state.vehicles = st.session_state.vehicles_slider

def priority(severity, traffic_level):
    score = {"Low": 1, "Medium": 2, "High": 3, "Critical": 4}[severity] * 2
    score += {"Low": 1, "Medium": 2, "High": 3}[traffic_level]
    level = ("Critical" if score >= 10 else "High" if score >= 8
             else "Medium" if score >= 5 else "Low")
    return score, level

def get_active_reservations():
    return [r for r in db.get_reservations() if r[5] == "Active"]

def get_all_hazards():
    return db.get_hazards()

def occupied_slots():
    return set(range(1, st.session_state.occupied + 1))
def reserved_slots():
    return {r[1] for r in get_active_reservations()}

def available_slots():
    return [s for s in range(1, TOTAL + 1)
            if s not in occupied_slots() | reserved_slots()]

def show_table(rows, fields):
    st.dataframe(
        [{label: row[index] for label, index in fields.items()} for row in rows],
        use_container_width=True, hide_index=True
    )

# ---------- NAVIGATION ----------
with st.sidebar:
    st.title("🚦 SmartCity")
    st.caption("TRAFFIC • PARKING • SAFETY")
    page = st.radio("NAVIGATION", [
        "Dashboard", "Traffic Management", "Smart Parking", "Road Safety"
    ])
    st.divider()
    st.success("Prototype running")
    st.caption("Demo data — no sensors connected")

level, signal, color = traffic(st.session_state.vehicles)
free = available_slots()
reservations = get_active_reservations()
hazards = get_all_hazards()

# =================================================
# DASHBOARD
# =================================================
if page == "Dashboard":
    vehicles = st.session_state.vehicles
    hero("Smart City Dashboard", "Traffic, parking and road safety at a glance.")
    st.info("Demonstration traffic/occupancy data only; map locations are illustrative.")

    a, b, c, d = st.columns(4)
    a.metric("Traffic", level, f'{vehicles} vehicles')
    b.metric("Available Slots", f"{len(free)}/{TOTAL}")
    c.metric("Reservations", len(reservations))
    d.metric("Unresolved Hazards", sum(r[7] != "Resolved" for r in hazards))

    left, right = st.columns(2)
    with left:
        st.subheader("Traffic Activity")
        st.write(f"Vehicles: **{st.session_state.vehicles}**")
        st.write(f"Traffic level: **{level}**")
        st.write(f"Suggested signal duration: **{signal} seconds**")

    with right:
        st.subheader("Parking Overview")
        st.write(f"Occupied slots: **{len(occupied_slots())}**")
        st.write(f"Reserved slots: **{len(reserved_slots())}**")
        st.write(f"Available slots: **{len(free)}**")
        st.caption("Occupied slots are simulated; reservations come from SQLite.")

    st.subheader("🗺️ Smart City Map")
    m = folium.Map(location=[16.99, 73.31], zoom_start=14)
    markers = [
        ([16.990, 73.305], f"Traffic: {level}", color, "car", "fa"),
        ([16.993, 73.312], f"Available parking: {len(free)}", "green", "info-sign", None),
        ([16.996, 73.319], f"Reported hazards: {len(hazards)}", "orange", "warning-sign", None)
    ]
    for location, popup, marker_color, icon, prefix in markers:
        options = {"color": marker_color, "icon": icon}
        if prefix:
            options["prefix"] = prefix
        folium.Marker(location, popup=popup, icon=folium.Icon(**options)).add_to(m)

    st_folium(m, height=400, use_container_width=True, key="dashboard_map")

    if hazards:
        st.subheader("Recent Hazards")
        show_table(hazards[:5], {
            "ID": 0, "Hazard": 1, "Location": 2,
            "Priority score": 6, "Status": 7, "Reported": 9
        })

# =================================================
# TRAFFIC MANAGEMENT
# =================================================
elif page == "Traffic Management":
    hero("Traffic Management", "Simulate vehicle density and signal timing.")

    st.slider(
        "Number of vehicles",
        0, 100,
        value=st.session_state.vehicles,
        key="vehicles_slider",
        on_change=update_vehicles
    )

    level, signal, _ = traffic(st.session_state.vehicles)

    a, b, c = st.columns(3)
    a.metric("Vehicles", st.session_state.vehicles)
    b.metric("Traffic Density", level)
    c.metric("Suggested Green Time", f"{signal} sec")

    st.progress(st.session_state.vehicles / 100)
    st.caption("Suggested timings are for demonstration, not real signal control.")
    if st.button("Save Traffic Reading", use_container_width=True):
        db.save_traffic(st.session_state.vehicles, level, signal)
        st.success("Traffic reading saved to the database.")

    st.subheader("Saved Traffic History")
    history = db.get_traffic_history()
    if history:
        show_table(history, {
            "Vehicles": 0, "Traffic level": 1,
            "Signal seconds": 2, "Saved at": 3
        })
    else:
        st.info("No traffic readings saved yet. Click 'Save Traffic Reading'.")

# =================================================
# SMART PARKING
# =================================================
elif page == "Smart Parking":
    hero("Smart Parking", "Check availability and reserve a parking slot.")
    st.warning("Occupancy is simulated. Reservations are stored in SQLite.")

    st.slider("Simulated occupied slots", 0, TOTAL, key="occupied")
    free = available_slots()
    reservations = get_active_reservations()

    a, b, c = st.columns(3)
    a.metric("Total", TOTAL)
    b.metric("Occupied (demo)", st.session_state.occupied)
    c.metric("Available", len(free))

    cols = st.columns(5)
    reserved_now = reserved_slots()
    for slot in range(1, TOTAL + 1):
        with cols[(slot - 1) % 5]:
          if slot in reserved_now:
           st.warning(f"Slot {slot}: Reserved")
          elif slot in occupied_slots():
           st.error(f"Slot {slot}: Occupied")
          else:
           st.success(f"Slot {slot}: Available")

           st.subheader("📅 Reserve a Slot")
    if free:
        with st.form("booking", clear_on_submit=True):
            name = st.text_input("Name")
            vehicle = st.text_input("Vehicle registration number")
            slot_num = st.selectbox("Available slot", free)
            book = st.form_submit_button("Confirm Reservation", use_container_width=True)

        if book:
            if not name.strip() or not vehicle.strip():
                st.error("Enter your name and vehicle number.")
            elif slot_num not in available_slots():
                st.error("That slot is no longer available. Refresh and try again.")
            else:
                rid = "RES-" + datetime.now().strftime("%Y%m%d-%H%M%S-%f")
                try:
                    db.save_reservation(rid, int(slot_num), name.strip(),
                                        vehicle.strip().upper())
                    st.success(f"Reservation confirmed! ID: {rid}")
                    st.rerun()
                except ValueError as error:
                    st.error(str(error))
    else:
        st.error("No available slots.")

    st.subheader("Reservation Records")
    reservations = get_active_reservations()
    if reservations:
        show_table(reservations, {
            "Reservation ID": 0, "Slot": 1, "Name": 2,
            "Vehicle": 3, "Created": 4, "Status": 5
        })
        choices = {f"{r[0]} — Slot {r[1]}": r[0] for r in reservations}
        selected = st.selectbox("Select reservation to cancel", list(choices))

        if st.button("Cancel Reservation"):
            if db.cancel_reservation(choices[selected]):
                st.success("Reservation cancelled and saved in the database.")
            else:
                st.warning("This reservation is already cancelled or does not exist.")
            st.rerun()
    else:
        st.info("No active reservations.")

    with st.expander("View reservation history"):
        all_reservations = db.get_reservations()
        if all_reservations:
            show_table(all_reservations, {
                "Reservation ID": 0, "Slot": 1, "Name": 2,
                "Vehicle": 3, "Created": 4, "Status": 5
            })
        else:
            st.info("No reservation history yet.")

# =================================================
# ROAD SAFETY
# =================================================
elif page == "Road Safety":
    hero("Road Safety Center", "Report hazards and track repair progress.")
    st.info("Hazard reports are saved in SQLite. Uploaded photos are stored in a local folder.")

    with st.form("hazard_form", clear_on_submit=True):
        kind = st.selectbox("Hazard type", [
            "Pothole", "Possible Accident", "Road Obstruction",
            "Damaged Streetlight", "Damaged Road Surface", "Waterlogging"
        ])
        location = st.text_input("Road / Location")
        severity = st.select_slider(
            "Severity", ["Low", "Medium", "High", "Critical"], value="Medium"
        )
        traffic_level = st.selectbox("Traffic level", ["Low", "Medium", "High"])
        description = st.text_area("Description")
        photo = st.file_uploader("Upload photo (optional)", type=["jpg", "jpeg", "png"])
        submit = st.form_submit_button("Submit Hazard Report", use_container_width=True)

    if submit:
        if not location.strip():
            st.error("Please enter a location.")
        else:
            score, priority_level = priority(severity, traffic_level)
            hid = "HAZ-" + datetime.now().strftime("%Y%m%d-%H%M%S-%f")
            photo_path = None

            if photo:
                photo_dir = Path("hazard_photos")
                photo_dir.mkdir(exist_ok=True)
                saved_photo = photo_dir / f"{hid}_{Path(photo.name).name}"
                saved_photo.write_bytes(photo.getvalue())
                photo_path = str(saved_photo)

            db.save_hazard(hid, kind, location.strip(), severity, traffic_level,
                           description.strip(), score, photo_path)
            st.success(f"Report {hid} submitted — {priority_level} priority.")
            st.rerun()

    hazards = get_all_hazards()
    st.subheader("Road Safety Statistics")
    a, b, c, d = st.columns(4)
    a.metric("Total Reports", len(hazards))
    b.metric("Critical Priority", sum(r[6] >= 10 for r in hazards))
    c.metric("Under Repair", sum(r[7] == "In Progress" for r in hazards))
    d.metric("Resolved", sum(r[7] == "Resolved" for r in hazards))

    st.subheader("Reports & Repair Tracking")
    if hazards:
        for r in hazards:
            hid, kind, location, severity, traffic_level, description, score, status, photo_path, created_at = r
            priority_level = (
                "Critical" if score >= 10 else "High" if score >= 8
                else "Medium" if score >= 5 else "Low"
            )

            with st.expander(f"{hid} | {kind} | {priority_level} priority"):
                st.write(f"**Location:** {location}")
                st.write(f"**Severity:** {severity} | **Traffic:** {traffic_level}")
                st.write(f"**Priority score:** {score}/11")
                st.write(f"**Reported:** {created_at}")
                st.write(description or "No description provided.")

                if photo_path and Path(photo_path).exists():
                    st.image(photo_path, caption=Path(photo_path).name,
                             use_container_width=True)

                statuses = ["Reported", "Verified", "In Progress", "Resolved"]
                status_index = statuses.index(status) if status in statuses else 0
                new_status = st.selectbox(
                    "Repair status", statuses, index=status_index, key=f"status_{hid}"
                )

                if st.button("Save Status", key=f"save_{hid}"):
                    db.update_hazard_status(hid, new_status)
                    st.success("Hazard status updated.")
                    st.rerun()
    else:
        st.info("No road hazards reported yet.")

# ---------- FOOTER ----------
st.divider()
st.caption(
    "SmartCity | Academic IoT prototype | Traffic and occupancy values "
    "are demo data; hardware is not connected."
)
