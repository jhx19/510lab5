import os

import requests
import streamlit as st
from dotenv import load_dotenv
from supabase import create_client


load_dotenv()
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")


st.set_page_config(page_title="GIX Events Board", layout="centered")


if SUPABASE_URL is None or SUPABASE_KEY is None:
    st.error("Missing Supabase credentials")
    st.stop()


supabase = create_client(SUPABASE_URL, SUPABASE_KEY)


def fetch_events():
    return (
        supabase.table("events")
        .select("id,title,description,category,event_date,location,created_at")
        .order("event_date", desc=False)
        .execute()
        .data
    )


try:
    events = fetch_events()
except requests.exceptions.Timeout:
    st.error("Connection timed out")
    st.stop()
except Exception:
    st.error("Could not load events. Please try again later.")
    st.stop()


try:
    assert isinstance(events, list), "Events query must return a list"
    assert all("title" in event for event in events), "Every event must have a title field"
except AssertionError as exc:
    st.warning(str(exc))


st.title("GIX Events Board")
st.caption("Upcoming events for the GIX community.")

categories = sorted(
    {
        event.get("category")
        for event in events
        if event.get("category") is not None and event.get("category") != ""
    }
)
selected_category = st.selectbox("Category", ["All"] + categories)

if selected_category == "All":
    filtered = events
else:
    filtered = [
        event for event in events if event.get("category") == selected_category
    ]

st.metric("Showing", f"{len(filtered)} event(s)")

if not filtered:
    st.info("No events found for this category.")
else:
    for event in filtered:
        with st.container():
            title = event.get("title", "Untitled event")
            event_date = event.get("event_date", "Date TBD")
            category = event.get("category", "Uncategorized")
            description = event.get("description", "")
            location = event.get("location", "Location TBD")

            st.markdown(f"**{title}** — {event_date}")
            st.caption(f"`{category}`")
            st.markdown(description)
            st.caption(f"Location: {location}")
        st.divider()
