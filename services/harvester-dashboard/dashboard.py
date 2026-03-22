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
if "selected_venue_id" not in st.session_state: st.session_state.selected_venue_id = None
if "geo_suggestions" not in st.session_state: st.session_state.geo_suggestions = []
if "venue_geo_suggestions" not in st.session_state: st.session_state.venue_geo_suggestions = []

# --- Data Logic ---
@st.cache_data(ttl=30)
def get_pending_events():
    with Session(engine) as session:
        statement = select(PendingEvent).where(PendingEvent.status == "pending").order_by(PendingEvent.location_name)
        return session.exec(statement).all()

@st.cache_data(ttl=30)
def get_venues(search_query: str = None, only_unverified: bool = False):
    with Session(engine) as session:
        statement = select(Venue).order_by(Venue.name)
        if search_query:
            statement = statement.where(Venue.name.ilike(f"%{search_query}%"))
        if only_unverified:
            statement = statement.where(Venue.is_manually_verified == False)
        return session.exec(statement).all()

def update_venue_record(venue_id: UUID, **kwargs):
    with Session(engine) as session:
        venue = session.get(Venue, venue_id)
        if venue:
            old_name = venue.name.strip()
            new_name = kwargs.get("name", old_name).strip()
            city = kwargs.get("city", venue.city)
            country_code = kwargs.get("country_code", venue.country_code)

            # Check for collisions: Can't have same name in same city
            if new_name != old_name or city != venue.city:
                existing = session.exec(
                    select(Venue).where(and_(
                        Venue.name == new_name, 
                        Venue.city == city, 
                        Venue.country_code == country_code, 
                        Venue.id != venue_id
                    ))
                ).first()
                if existing:
                    st.error(f"A venue named '{new_name}' already exists in '{city}'. Use the 'Merge' tool or choose a different name.")
                    return False
            
            # Update venue record
            for k, v in kwargs.items(): setattr(venue, k, v)
            session.add(venue)
            # ... (rest of logic)
            
            # Sync to events if location or name changed
            if any(k in kwargs for k in ["lat", "lng", "name", "full_address", "is_manually_verified"]):
                lat = kwargs.get("lat", venue.lat)
                lng = kwargs.get("lng", venue.lng)
                status = "verified" if kwargs.get("is_manually_verified", venue.is_manually_verified) else "ambiguous"
                
                # Sync PendingEvent
                statement_pending = select(PendingEvent).where(PendingEvent.location_name == old_name)
                linked_pending = session.exec(statement_pending).all()
                for ev in linked_pending:
                    ev.location_name = new_name
                    ev.location = WKTElement(f"POINT({lng} {lat})", srid=4326)
                    ev.geocoding_status = status
                    ev.geocoding_metadata = {
                        "source": "manual_sync",
                        "full_address": kwargs.get("full_address", venue.full_address),
                        "city": kwargs.get("city", venue.city)
                    }
                    session.add(ev)
                
                # Sync published Event
                statement_events = select(Event).where(Event.location_name == old_name)
                linked_events = session.exec(statement_events).all()
                for ev in linked_events:
                    ev.location_name = new_name
                    ev.location = WKTElement(f"POINT({lng} {lat})", srid=4326)
                    session.add(ev)
            
            session.commit()
            st.cache_data.clear()
            return True
    return False

def merge_venues(source_venue_id: UUID, target_venue_id: UUID):
    """Merges source venue into target venue, updating all linked events."""
    with Session(engine) as session:
        source = session.get(Venue, source_venue_id)
        target = session.get(Venue, target_venue_id)
        
        if not source or not target: return False
        
        source_name = source.name.strip()
        target_name = target.name.strip()
        
        # 1. Update all events linked to source name to use target name and target location
        target_wkt = f"POINT({target.lng} {target.lat})"
        
        # Sync PendingEvent
        statement_pending = select(PendingEvent).where(PendingEvent.location_name == source_name)
        linked_pending = session.exec(statement_pending).all()
        for ev in linked_pending:
            ev.location_name = target_name
            ev.location = WKTElement(target_wkt, srid=4326)
            ev.geocoding_status = "verified" if target.is_manually_verified else "ambiguous"
            session.add(ev)
            
        # Sync published Event
        statement_events = select(Event).where(Event.location_name == source_name)
        linked_events = session.exec(statement_events).all()
        for ev in linked_events:
            ev.location_name = target_name
            ev.location = WKTElement(target_wkt, srid=4326)
            session.add(ev)
            
        # 2. Delete source venue
        session.delete(source)
        session.commit()
        st.cache_data.clear()
        return True


def delete_venue_and_unlink_events(venue_id: UUID):
    with Session(engine) as session:
        venue = session.get(Venue, venue_id)
        if venue:
            venue_name = venue.name.strip()
            
            # Unlink PendingEvent
            statement_pending = select(PendingEvent).where(PendingEvent.location_name == venue_name)
            linked_pending = session.exec(statement_pending).all()
            for ev in linked_pending:
                ev.location = None
                ev.geocoding_status = "failed"
                ev.confidence_score = None
                ev.geocoding_metadata = {}
                session.add(ev)

            # Unlink published Event
            statement_events = select(Event).where(Event.location_name == venue_name)
            linked_events = session.exec(statement_events).all()
            for ev in linked_events:
                ev.location = None
                session.add(ev)
            
            # Delete venue
            session.delete(venue)
            session.commit()
            st.cache_data.clear()
            return True
    return False

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
                    city = pending.geocoding_metadata.get("city")
                    venue = session.exec(
                        select(Venue).where(and_(
                            Venue.name == pending.location_name.strip(), 
                            Venue.city == city,
                            Venue.country_code == pending.country_code
                        ))
                    ).first()
                    
                    if not venue:
                        new_venue = Venue(
                            name=pending.location_name.strip(),
                            country_code=pending.country_code or "GR",
                            city=city,
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
        # Try to find venue by coordinates (approx) or name + city
        venue = session.exec(
            select(Venue).where(and_(
                Venue.name == name, 
                Venue.city == res.city,
                Venue.country_code == country_code
            ))
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
        # Sync PendingEvent
        all_pending = session.exec(select(PendingEvent)).all()
        for p in all_pending:
            if p.location_name and p.location_name.strip() == target_clean:
                p.location = WKTElement(location_wkt, srid=4326)
                p.geocoding_status = status
                p.confidence_score = confidence
                p.geocoding_metadata = metadata
                session.add(p)
        
        # Sync published Event
        all_events = session.exec(select(Event)).all()
        for e in all_events:
            if e.location_name and e.location_name.strip() == target_clean:
                e.location = WKTElement(location_wkt, srid=4326)
                session.add(e)

        session.commit()
        st.cache_data.clear()

# --- UI Execution ---
tab_events, tab_venues = st.tabs(["🛡️ Events Moderation", "📍 Venue Management"])

with tab_events:
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
        
        if filtered:
            c_bulk_app, c_bulk_rej = st.columns(2)
            if c_bulk_app.button("✅ Approve All", key="bulk_approve", type="primary"):
                approve_events([e.id for e in filtered])
                st.toast(f"Approved {len(filtered)} events!")
                st.rerun()
            if c_bulk_rej.button("❌ Reject All", key="bulk_reject"):
                reject_events([e.id for e in filtered])
                st.toast(f"Rejected {len(filtered)} events!")
                st.rerun()

        st.write("---")
        
        if not filtered:
            st.info("No events matching filters.")
        
        for e in filtered:
            c_btn, c_app, c_rej = st.columns([4, 1, 1])
            emoji = STATUS_EMOJI.get(e.geocoding_status, "⚪")
            
            # Extract image from metadata
            img_url = e.event_metadata.get("image") or e.event_metadata.get("photo_url") or e.event_metadata.get("cover")
            
            with c_btn:
                btn_label = f"{emoji} {e.title[:22]}"
                if st.button(btn_label, key=f"s_{e.id}"):
                    st.session_state.selected_event_id = e.id
                    st.session_state.geo_suggestions = []
                    st.rerun()
                if img_url:
                    st.image(img_url, width=100)
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
                    # Extract and show large image
                    img_url = curr.event_metadata.get("image") or curr.event_metadata.get("photo_url") or curr.event_metadata.get("cover")
                    if img_url:
                        st.image(img_url, use_container_width=True)
                    
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

with tab_venues:
    st.header("📍 Venue Management")
    
    # --- Filtering ---
    c_v1, c_v2 = st.columns([2, 1])
    v_search = c_v1.text_input("🔍 Search Venues", placeholder="Filter by name...", key="v_search_top")
    v_unverified = c_v2.checkbox("Show only unverified venues", value=True, key="v_unverified_top")
    
    all_v = get_venues(v_search, v_unverified)
    
    col_vmap, col_vinsp = st.columns([1.5, 1])
    
    with col_vmap:
        # Prepare Map Data
        map_v_data = []
        for v in all_v:
            map_v_data.append({
                "id": str(v.id),
                "name": v.name,
                "lat": v.lat,
                "lon": v.lng,
                "type": "Venue",
                "status": "Verified" if v.is_manually_verified else "Unverified",
                "color": "#238636" if v.is_manually_verified else "#d29922",
                "size": 15 if st.session_state.selected_venue_id == v.id else 10
            })
        
        # Add Suggestions to Map if searching
        if st.session_state.venue_geo_suggestions:
            for i, s in enumerate(st.session_state.venue_geo_suggestions):
                map_v_data.append({
                    "id": f"sugg_{i}",
                    "name": f"Suggestion: {s.full_address}",
                    "lat": s.lat,
                    "lon": s.lng,
                    "type": "Suggestion",
                    "status": "Mapbox Match",
                    "color": "#58a6ff", # Blue for suggestions
                    "size": 12
                })

        if map_v_data:
            df_v = pd.DataFrame(map_v_data)
            
            # Center on selected venue or suggestion
            if st.session_state.selected_venue_id:
                sel_v = next((v for v in all_v if v.id == st.session_state.selected_venue_id), None)
                if sel_v:
                    v_center = {"lat": sel_v.lat, "lon": sel_v.lng}
                    v_zoom = 15
                else:
                    v_center = {"lat": df_v['lat'].mean(), "lon": df_v['lon'].mean()}
                    v_zoom = 11
            else:
                v_center = {"lat": df_v['lat'].mean(), "lon": df_v['lon'].mean()}
                v_zoom = 11

            fig_v = px.scatter_mapbox(
                df_v, lat="lat", lon="lon", hover_name="name",
                color="color", color_discrete_map="identity",
                size="size", zoom=v_zoom, center=v_center,
                mapbox_style="carto-darkmatter", height=700
            )
            fig_v.update_layout(margin={"r":0,"t":0,"l":0,"b":0}, paper_bgcolor="#0D1117", showlegend=False)
            
            # Selection logic
            v_select = st.plotly_chart(fig_v, on_select="rerun", selection_mode="points", use_container_width=True, config={'displayModeBar': False}, key="v_map_chart")
            
            if v_select and v_select.get("selection") and v_select["selection"].get("points"):
                try:
                    p = v_select["selection"]["points"][0]
                    # Mapbox Suggestion click doesn't have an ID in df_v that matches UUID
                    clicked_id_str = df_v[(df_v['lat'] == p['lat']) & (df_v['lon'] == p['lon'])].iloc[0]['id']
                    if not clicked_id_str.startswith("sugg_"):
                        st.session_state.selected_venue_id = UUID(clicked_id_str)
                        st.session_state.venue_geo_suggestions = []
                        st.rerun()
                except: pass
        else:
            st.info("No venues found matching filters.")

        # --- Venue List Table (Below Map) ---
        st.markdown("---")
        st.subheader("📋 Venue List")
        if all_v:
            v_table_data = []
            for v in all_v:
                v_table_data.append({
                    "Name": v.name,
                    "City": v.city or "N/A",
                    "Address": v.full_address,
                    "Verified": "✅" if v.is_manually_verified else "🟡",
                    "Relevance": f"{v.relevance:.2f}",
                    "ID": str(v.id)
                })
            
            v_df = pd.DataFrame(v_table_data)
            v_selection = st.dataframe(
                v_df, 
                use_container_width=True, 
                hide_index=True,
                on_select="rerun",
                selection_mode="single-row",
                key="v_data_table"
            )
            
            if v_selection and v_selection.get("selection") and v_selection["selection"].get("rows"):
                try:
                    selected_row_idx = v_selection["selection"]["rows"][0]
                    selected_v_id_str = v_df.iloc[selected_row_idx]["ID"]
                    selected_v_id = UUID(selected_v_id_str)
                    if st.session_state.selected_venue_id != selected_v_id:
                        st.session_state.selected_venue_id = selected_v_id
                        st.session_state.venue_geo_suggestions = []
                        st.rerun()
                except Exception: pass
            
            st.caption("Tip: Select a venue from the table or map to edit its details.")
        else:
            st.write("No venues to display.")

    with col_vinsp:
        # Venue List Selector (compact)
        if all_v:
            v_names = {f"{v.name} ({v.city or 'Unknown'})": v.id for v in all_v}
            # Find current index for selectbox
            curr_idx = 0
            if st.session_state.selected_venue_id:
                for i, vid in enumerate(v_names.values()):
                    if vid == st.session_state.selected_venue_id:
                        curr_idx = i; break
            
            selected_v_id = st.selectbox("🎯 Select Venue", list(v_names.keys()), index=curr_idx)
            if v_names[selected_v_id] != st.session_state.selected_venue_id:
                st.session_state.selected_venue_id = v_names[selected_v_id]
                st.session_state.venue_geo_suggestions = []
                st.rerun()
        
        if st.session_state.selected_venue_id:
            v_curr = next((v for v in all_v if v.id == st.session_state.selected_venue_id), None)
            
            if v_curr:
                with st.container(border=True):
                    st.subheader(f"Editing: {v_curr.name}")
                    
                    v_name = st.text_input("Venue Name", value=v_curr.name, key="edit_v_name")
                    v_city = st.text_input("City", value=v_curr.city or "", key="edit_v_city")
                    v_address = st.text_area("Full Address", value=v_curr.full_address, key="edit_v_addr")
                    
                    c_lat, c_lng = st.columns(2)
                    v_lat = c_lat.number_input("Latitude", value=v_curr.lat, format="%.6f")
                    v_lng = c_lng.number_input("Longitude", value=v_curr.lng, format="%.6f")
                    
                    v_verified = st.toggle("Manually Verified", value=v_curr.is_manually_verified)
                    v_auto_publish = st.checkbox("🚀 Auto-publish matching events on verification", value=True)
                    
                    if st.button("💾 Save Venue Changes"):
                        update_venue_record(v_curr.id, 
                            name=v_name, city=v_city, full_address=v_address, 
                            lat=v_lat, lng=v_lng, is_manually_verified=v_verified
                        )
                        if v_verified and v_auto_publish:
                            with Session(engine) as session:
                                linked_pending = session.exec(select(PendingEvent).where(PendingEvent.location_name == v_curr.name.strip())).all()
                                if linked_pending:
                                    approve_events([lp.id for lp in linked_pending])
                                    st.toast(f"Published {len(linked_pending)} linked events!")
                        
                        st.success("Venue updated successfully!")
                        st.rerun()
                    
                    st.markdown("---")
                    st.markdown("##### 🔍 Search Mapbox Suggestion")
                    vq = st.text_input("Search address/venue...", value=v_name if not st.session_state.venue_geo_suggestions else "", key="v_geo_search")
                    if st.button("🔍 Search Mapbox", key="v_geo_btn"):
                        with st.spinner("Searching..."):
                            st.session_state.venue_geo_suggestions = asyncio.run(GeocoderService.get_suggestions(vq, v_curr.country_code or "GR"))
                            st.rerun()
                    
                    if st.session_state.venue_geo_suggestions:
                        st.info("💡 Suggestions appear as **blue** dots on the map.")
                        v_sugg_options = {f"{s.full_address} (Rel: {s.relevance})": s for s in st.session_state.venue_geo_suggestions}
                        v_selected_label = st.radio("Pick a suggestion:", list(v_sugg_options.keys()), key="v_geo_radio")
                        
                        if st.button("📍 Apply Suggestion & Sync All Events", key="v_geo_apply"):
                            v_res = v_sugg_options[v_selected_label]
                            
                            # 1. Update Venue
                            update_venue_record(v_curr.id, 
                                full_address=v_res.full_address,
                                lat=v_res.lat,
                                lng=v_res.lng,
                                city=v_res.city,
                                relevance=v_res.relevance,
                                is_manually_verified=True
                            )
                            
                            # 2. Automatically sync to all matching events
                            batch_update_location(
                                v_curr.name,
                                f"POINT({v_res.lng} {v_res.lat})",
                                "verified",
                                v_res.relevance,
                                {"source": "manual_verify", "full_address": v_res.full_address, "city": v_res.city}
                            )

                            # 3. Auto-publish if requested
                            if v_auto_publish:
                                with Session(engine) as session:
                                    linked_pending = session.exec(select(PendingEvent).where(PendingEvent.location_name == v_curr.name.strip())).all()
                                    if linked_pending:
                                        approve_events([lp.id for lp in linked_pending])
                                        st.toast(f"Published {len(linked_pending)} linked events!")
                            
                            st.session_state.venue_geo_suggestions = []
                            st.success(f"Venue verified and all matching events updated!")
                            st.rerun()
                    
                    # --- Linked Events Section ---
                    st.markdown("---")
                    st.markdown("🔗 **Linked Pending Events**")
                    with Session(engine) as session:
                        linked = session.exec(select(PendingEvent).where(PendingEvent.location_name == v_curr.name.strip())).all()
                    
                    if linked:
                        for le in linked:
                            l_col1, l_col2 = st.columns([3, 1])
                            l_col1.caption(f"**{le.title}**")
                            if le.source_url:
                                l_col2.link_button("📄 Source", le.source_url)
                    else:
                        st.write("No pending events linked to this venue name.")

                    st.markdown("---")
                    if st.button("🔄 Manual Sync All Events"):
                        wkt = f"POINT({v_curr.lng} {v_curr.lat})"
                        batch_update_location(
                            v_curr.name,
                            wkt,
                            "verified" if v_curr.is_manually_verified else "ambiguous",
                            v_curr.relevance,
                            {"source": "manual_sync", "full_address": v_curr.full_address, "city": v_curr.city}
                        )
                        st.success(f"Updated all events matching '{v_curr.name}'")
                    
                    st.markdown("---")
                    st.markdown("##### 🧩 Merge Duplicates")
                    st.caption("Merge this venue INTO another existing venue. This will update all linked events and delete this record.")
                    other_venues = [v for v in all_v if v.id != v_curr.id]
                    if other_venues:
                        target_v_names = {f"{v.name} ({v.city or 'Unknown'})": v.id for v in other_venues}
                        target_v_label = st.selectbox("Select Target Venue", list(target_v_names.keys()), key="merge_target")
                        if st.button("Merge INTO Target Venue", type="secondary"):
                            target_id = target_v_names[target_v_label]
                            if merge_venues(v_curr.id, target_id):
                                st.session_state.selected_venue_id = target_id
                                st.success(f"Successfully merged '{v_curr.name}' into target!")
                                st.rerun()
                    else:
                        st.info("No other venues to merge with.")

                    st.markdown("---")
                    st.markdown("##### ⚠️ Danger Zone")
                    if st.button("🗑️ Delete Venue & Unlink Events", type="primary", use_container_width=True):
                        delete_venue_and_unlink_events(v_curr.id)
                        st.session_state.selected_venue_id = None
                        st.success(f"Deleted venue '{v_curr.name}' and unlinked related events.")
                        st.rerun()
        else:
            st.info("👈 Select a venue to edit")

