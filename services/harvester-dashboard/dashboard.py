import streamlit as st
import pandas as pd
import plotly.express as px
from sqlmodel import Session, select, create_engine, and_
from uuid import UUID, uuid4
import os
import sys
import asyncio
from datetime import datetime, time

# Add services/api to sys.path to import models
api_path = os.path.abspath(os.path.join(os.getcwd(), "..", "api"))
if not os.path.exists(api_path):
    api_path = "/app/services/api"
if api_path not in sys.path:
    sys.path.append(api_path)

from app.models.event import Event, PendingEvent
from app.models.venue import Venue
from app.services.harvester.geocoder import GeocoderService, GeocodeResult
from app.core.config import settings
from geoalchemy2.shape import to_shape
from geoalchemy2.elements import WKTElement

# Database connection
engine = create_engine(settings.DATABASE_URL)

st.set_page_config(page_title="FOMO Moderator", layout="wide", initial_sidebar_state="expanded")

# --- UI Constants & Theme ---
CATEGORIES = ["Music", "Art", "Tech", "Food", "Nightlife", "Sports", "Other"]
STATUS_COLORS_HEX = {"verified": "#238636", "ambiguous": "#d29922", "failed": "#f85149"}
STATUS_EMOJI = {"verified": "🟢", "ambiguous": "🟡", "failed": "🔴"}

st.markdown("""
    <style>
    .stApp { background-color: #0D1117; color: #C9D1D9; font-family: 'Inter', sans-serif; }
    [data-testid="stSidebar"] { background-color: #010409; border-right: 1px solid #30363d; }
    .stButton>button { border-radius: 6px; border: 1px solid #30363d; background-color: #21262d; color: #c9d1d9; width: 100%; }
    .stButton>button:hover { border-color: #8b949e; background-color: #30363d; }
    div[data-testid="stVerticalBlock"] > div[style*="border"] { background-color: #161b22 !important; border: 1px solid #30363d !important; border-radius: 8px !important; }
    /* Hide Plotly modebar and extra white space */
    .modebar { display: none !important; }
    .main .block-container { padding-top: 2rem; padding-bottom: 2rem; }
    </style>
    """, unsafe_allow_html=True)

# --- State Management ---
if "selected_event_id" not in st.session_state: st.session_state.selected_event_id = None
if "geo_suggestions" not in st.session_state: st.session_state.geo_suggestions = []

# --- Data Logic ---
@st.cache_data(ttl=30)
def get_pending_events():
    with Session(engine) as session:
        statement = select(PendingEvent).where(PendingEvent.status == "pending").order_by(PendingEvent.location_name)
        return session.exec(statement).all()

def approve_events(event_ids: list[UUID]):
    with Session(engine) as session:
        for eid in event_ids:
            pending = session.get(PendingEvent, eid)
            if pending and pending.status == "pending":
                # 1. Create the primary live event
                primary_id = uuid4()
                live_event = Event(
                    id=primary_id,
                    title=pending.title, location=pending.location, start_time=pending.start_time,
                    end_time=pending.end_time, category=pending.category, hype_score=pending.hype_score,
                    ticket_url=pending.ticket_url, source_url=pending.source_url, event_metadata=pending.event_metadata,
                    location_name=pending.location_name, country_code=pending.country_code,
                    parent_id=pending.parent_id or primary_id 
                )
                session.add(live_event)
                
                # 2. Handle Venue sync on approval if geocoded
                if pending.location_name and pending.geocoding_status == "verified" and pending.location:
                    shape = to_shape(pending.location)
                    venue = session.exec(
                        select(Venue).where(and_(
                            Venue.name == pending.location_name.strip(), 
                            Venue.country_code == pending.country_code
                        ))
                    ).first()
                    
                    if not venue:
                        new_venue = Venue(
                            name=pending.location_name.strip(),
                            country_code=pending.country_code or "GR",
                            city=pending.geocoding_metadata.get("city"),
                            lat=shape.y,
                            lng=shape.x,
                            full_address=pending.geocoding_metadata.get("full_address") or pending.location_name,
                            relevance=pending.confidence_score or 1.0
                        )
                        session.add(new_venue)
                
                pending.status = "published"
                session.add(pending)
        session.commit()
        st.cache_data.clear()

def reject_events(event_ids: list[UUID]):
    with Session(engine) as session:
        for eid in event_ids:
            pending = session.get(PendingEvent, eid)
            if pending:
                session.delete(pending)
        session.commit()
        st.cache_data.clear()

def update_pending_event(event_id: UUID, **kwargs):
    with Session(engine) as session:
        pending = session.get(PendingEvent, event_id)
        if pending:
            # Check if location_name is changing to update Venue table as well
            old_name = pending.location_name
            new_name = kwargs.get("location_name")
            
            if new_name is not None:
                new_name = new_name.strip()
                kwargs["location_name"] = new_name
            
            for k, v in kwargs.items(): setattr(pending, k, v)
            
            if new_name and old_name and new_name != old_name.strip():
                old_name_clean = old_name.strip()
                
                # Update Venue table if a venue with old_name exists
                venue = session.exec(
                    select(Venue).where(and_(Venue.name == old_name_clean, Venue.country_code == pending.country_code))
                ).first()
                if venue:
                    venue.name = new_name
                    session.add(venue)
                
                # Update all other pending events that had the exact same old location name (ignoring spaces)
                all_pending = session.exec(select(PendingEvent)).all()
                for p in all_pending:
                    if p.id != pending.id and p.location_name and p.location_name.strip() == old_name_clean:
                        p.location_name = new_name
                        session.add(p)
            
            session.add(pending)
            session.commit()
            st.cache_data.clear()
            return True
    return False

def save_or_update_venue(name: str, res: GeocodeResult, country_code: str):
    name = name.strip() if name else ""
    with Session(engine) as session:
        # Try to find venue by coordinates (approx) or name
        venue = session.exec(
            select(Venue).where(and_(Venue.name == name, Venue.country_code == country_code))
        ).first()
        
        if venue:
            venue.lat = res.lat
            venue.lng = res.lng
            venue.full_address = res.full_address
            venue.city = res.city
            venue.relevance = res.relevance
        else:
            venue = Venue(
                name=name, country_code=country_code, city=res.city,
                lat=res.lat, lng=res.lng, full_address=res.full_address, relevance=res.relevance
            )
        session.add(venue)
        session.commit()

def batch_update_location(target_name: str, location_wkt: str, status: str, confidence: float, metadata: dict):
    if not target_name: return
    target_clean = target_name.strip()
    with Session(engine) as session:
        all_pending = session.exec(select(PendingEvent)).all()
        for p in all_pending:
            if p.location_name and p.location_name.strip() == target_clean:
                p.location = WKTElement(location_wkt, srid=4326)
                p.geocoding_status = status
                p.confidence_score = confidence
                p.geocoding_metadata = metadata
                session.add(p)
        session.commit()
        st.cache_data.clear()

# --- UI Execution ---
events = get_pending_events()

with st.sidebar:
    st.title("🛡️ FOMO")
    st.caption(f"{len(events)} pending events")
    st.write("---")
    
    st.subheader("Filters")
    locations = sorted(list(set(e.location_name or "Unknown" for e in events)))
    selected_loc = st.selectbox("Location Filter", ["All Locations"] + locations, key="loc_filter")
    
    statuses = ["verified", "ambiguous", "failed"]
    selected_statuses = st.multiselect("Status Filter", statuses, default=statuses, key="stat_filter")
    
    # Combined filtering logic
    filtered = [
        e for e in events 
        if (selected_loc == "All Locations" or e.location_name == selected_loc)
        and (e.geocoding_status in selected_statuses)
    ]
    
    st.write(f"Showing **{len(filtered)}** events")
    st.write("---")
    
    if not filtered:
        st.info("No events matching filters.")
    
    for e in filtered:
        c_btn, c_app, c_rej = st.columns([4, 1, 1])
        emoji = STATUS_EMOJI.get(e.geocoding_status, "⚪")
        with c_btn:
            if st.button(f"{emoji} {e.title[:22]}", key=f"s_{e.id}"):
                st.session_state.selected_event_id = e.id
                st.session_state.geo_suggestions = []
                st.rerun()
        with c_app:
            if st.button("✅", key=f"q_{e.id}"):
                approve_events([e.id]); st.toast("Published!"); st.rerun()
        with c_rej:
            if st.button("❌", key=f"r_{e.id}"):
                reject_events([e.id]); st.toast("Rejected!"); st.rerun()

# --- Main Dashboard ---
col_map, col_insp = st.columns([1.5, 1])

with col_map:
    # Prepare Dataframe for Plotly Map
    map_data = []
    for e in events:
        if e.location:
            shape = to_shape(e.location)
            map_data.append({
                "id": str(e.id),
                "title": e.title,
                "lat": shape.y,
                "lon": shape.x,
                "status": e.geocoding_status,
                "color": STATUS_COLORS_HEX.get(e.geocoding_status, "#808080"),
                "size": 12 if st.session_state.selected_event_id == e.id else 8
            })
    
    if map_data:
        df = pd.DataFrame(map_data)
        
        # Center and Zoom Logic
        if st.session_state.selected_event_id:
            sel_row = df[df['id'] == str(st.session_state.selected_event_id)]
            if not sel_row.empty:
                center = {"lat": sel_row['lat'].iloc[0], "lon": sel_row['lon'].iloc[0]}
                zoom = 16
            else:
                center = {"lat": df['lat'].mean(), "lon": df['lon'].mean()}
                zoom = 11
        else:
            center = {"lat": df['lat'].mean(), "lon": df['lon'].mean()}
            zoom = 11

        fig = px.scatter_mapbox(
            df,
            lat="lat",
            lon="lon",
            hover_name="title",
            hover_data={"id": False, "lat": False, "lon": False, "status": True},
            color="status",
            color_discrete_map={k: v for k, v in STATUS_COLORS_HEX.items()},
            size="size",
            zoom=zoom,
            center=center,
            mapbox_style="carto-darkmatter"
        )
        # Fix white sidebar: set paper_bgcolor and plot_bgcolor to dark, hide modebar
        fig.update_layout(
            margin={"r":0,"t":0,"l":0,"b":0}, 
            height=650,
            paper_bgcolor="#0D1117",
            plot_bgcolor="#0D1117",
            showlegend=False
        )
        
        try:
            selection = st.plotly_chart(fig, on_select="rerun", selection_mode="points", use_container_width=True, config={'displayModeBar': False})
            
            if selection and selection.get("selection") and selection["selection"].get("points"):
                try:
                    point = selection["selection"]["points"][0]
                    clicked_lat = point["lat"]
                    clicked_lon = point["lon"]
                    matching_row = df[(df['lat'] == clicked_lat) & (df['lon'] == clicked_lon)]
                    if not matching_row.empty:
                        clicked_id = UUID(matching_row.iloc[0]["id"])
                        if st.session_state.selected_event_id != clicked_id:
                            st.session_state.selected_event_id = clicked_id
                            st.session_state.geo_suggestions = []
                            st.rerun()
                except: pass
        except TypeError:
            st.plotly_chart(fig, use_container_width=True, config={'displayModeBar': False})
    else:
        st.info("No mapped events available.")

with col_insp:
    if st.session_state.selected_event_id:
        curr = next((e for e in events if e.id == st.session_state.selected_event_id), None)
        if curr:
            with st.container(border=True):
                st.markdown(f"### Edit Event")
                
                # --- Basic Fields ---
                new_title = st.text_input("Event Title", value=curr.title)
                if new_title != curr.title:
                    if st.button("💾 Update Title"):
                        update_pending_event(curr.id, title=new_title); st.rerun()
                
                c_date, c_time = st.columns(2)
                with c_date:
                    new_date = st.date_input("Start Date", value=curr.start_time.date())
                with c_time:
                    new_time = st.time_input("Start Time", value=curr.start_time.time())
                
                new_start_time = datetime.combine(new_date, new_time).replace(tzinfo=curr.start_time.tzinfo)
                if new_start_time != curr.start_time:
                    if st.button("💾 Update Start Time"):
                        update_pending_event(curr.id, start_time=new_start_time); st.rerun()

                new_name = st.text_input("Venue Name", value=curr.location_name or "")
                if new_name != curr.location_name:
                    if st.button("💾 Rename Venue & Sync Table"):
                        update_pending_event(curr.id, location_name=new_name); st.rerun()
                
                c_cat, c_hype = st.columns(2)
                with c_cat:
                    idx = CATEGORIES.index(curr.category) if curr.category in CATEGORIES else CATEGORIES.index("Other")
                    new_cat = st.selectbox("Category", CATEGORIES, index=idx)
                    if new_cat != curr.category:
                        update_pending_event(curr.id, category=new_cat); st.rerun()
                with c_hype:
                    new_hype = st.number_input("Hype Score", value=curr.hype_score, step=1)
                    if new_hype != curr.hype_score:
                        if st.button("💾 Update Hype"):
                            update_pending_event(curr.id, hype_score=new_hype); st.rerun()
                
                new_ticket = st.text_input("Ticket URL", value=curr.ticket_url or "")
                if new_ticket != curr.ticket_url:
                    if st.button("💾 Update Ticket URL"):
                        update_pending_event(curr.id, ticket_url=new_ticket); st.rerun()

                # --- Multi-day Occurrences ---
                st.markdown("---")
                st.markdown("📅 **Additional Dates (Multi-day)**")
                occurrences = curr.event_metadata.get("occurrences", [])
                
                for i, occ in enumerate(occurrences):
                    occ_dt = datetime.fromisoformat(occ["start_time"])
                    col_occ_txt, col_occ_del = st.columns([4, 1])
                    col_occ_txt.write(f"Occurrence {i+1}: {occ_dt.strftime('%Y-%m-%d %H:%M')}")
                    if col_occ_del.button("🗑️", key=f"del_occ_{i}"):
                        occurrences.pop(i)
                        update_pending_event(curr.id, event_metadata={**curr.event_metadata, "occurrences": occurrences})
                        st.rerun()

                with st.expander("➕ Add Another Date"):
                    new_occ_date = st.date_input("Date", value=curr.start_time.date(), key="new_occ_date")
                    new_occ_time = st.time_input("Time", value=curr.start_time.time(), key="new_occ_time")
                    if st.button("Add Date"):
                        new_occ_dt = datetime.combine(new_occ_date, new_occ_time).replace(tzinfo=curr.start_time.tzinfo)
                        
                        # Create a new PendingEvent record for this occurrence
                        with Session(engine) as session:
                            # Primary parent ID is either the current event's parent_id or its own ID
                            parent_id = curr.parent_id or curr.id
                            
                            # Ensure the current event also has its parent_id set if it was the first
                            if not curr.parent_id:
                                curr_db = session.get(PendingEvent, curr.id)
                                if curr_db:
                                    curr_db.parent_id = parent_id
                                    session.add(curr_db)

                            new_pending = PendingEvent(
                                title=curr.title,
                                location=curr.location,
                                location_name=curr.location_name,
                                country_code=curr.country_code,
                                start_time=new_occ_dt,
                                category=curr.category,
                                hype_score=curr.hype_score,
                                ticket_url=curr.ticket_url,
                                source_url=curr.source_url,
                                event_metadata=curr.event_metadata,
                                confidence_score=curr.confidence_score,
                                geocoding_status=curr.geocoding_status,
                                geocoding_metadata=curr.geocoding_metadata,
                                status="pending",
                                parent_id=parent_id
                            )
                            session.add(new_pending)
                            session.commit()
                        
                        st.toast("New occurrence added to pending list!")
                        st.cache_data.clear()
                        st.rerun()

                if curr.source_url: st.link_button("🔗 View Original Source", curr.source_url)
                
                c_app_btn, c_rej_btn = st.columns(2)
                with c_app_btn:
                    if st.button("✅ Approve & Publish", type="primary", use_container_width=True):
                        approve_events([curr.id]); st.session_state.selected_event_id = None; st.toast("Published!"); st.rerun()
                with c_rej_btn:
                    if st.button("❌ Reject & Delete", type="secondary", use_container_width=True):
                        reject_events([curr.id]); st.session_state.selected_event_id = None; st.toast("Rejected!"); st.rerun()
                
                # --- Advanced Location Search ---
                st.markdown("---")
                st.markdown("##### 📍 Search Location Suggestions")
                q = st.text_input("Search address/venue...", value=new_name if not st.session_state.geo_suggestions else "")
                if st.button("🔍 Search Mapbox"):
                    with st.spinner("Searching..."):
                        st.session_state.geo_suggestions = asyncio.run(GeocoderService.get_suggestions(q, curr.country_code or "GR"))
                        st.rerun()
                
                if st.session_state.geo_suggestions:
                    # Show venue AND full address
                    sugg_options = {f"{s.full_address} (Relevance: {s.relevance})": s for s in st.session_state.geo_suggestions}
                    selected_sugg_label = st.radio("Suggestions found:", list(sugg_options.keys()))
                    
                    if st.button("📍 Apply Location & Update Venue Table"):
                        res = sugg_options[selected_sugg_label]
                        wkt_str = f"POINT({res.lng} {res.lat})"
                        
                        # First update the single event to guarantee it updates (even if it lacks a location name)
                        update_pending_event(curr.id, 
                            location=WKTElement(wkt_str, srid=4326),
                            geocoding_status=res.geocoding_status,
                            confidence_score=res.relevance,
                            geocoding_metadata=res.geocoding_metadata
                        )
                        
                        # Batch update all other events with the exact same location name
                        if curr.location_name:
                            batch_update_location(
                                curr.location_name,
                                wkt_str,
                                res.geocoding_status,
                                res.relevance,
                                res.geocoding_metadata
                            )
                            
                        # Sync to venues table
                        save_or_update_venue(new_name or res.full_address, res, curr.country_code or "GR")
                        st.session_state.geo_suggestions = []
                        st.toast("Location Updated & Venue Synced for all matching events!"); st.rerun()
    else: st.info("👈 Select an event to begin.")
