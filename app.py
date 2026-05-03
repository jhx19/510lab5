import os
from io import StringIO

import pandas as pd
import requests
import streamlit as st
from dotenv import load_dotenv
from supabase import create_client


load_dotenv()
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")


st.set_page_config(page_title="GIX Inventory Pre-Processor", layout="wide")


if SUPABASE_URL is None or SUPABASE_KEY is None:
    st.error("Missing Supabase credentials")
    st.stop()


supabase = create_client(SUPABASE_URL, SUPABASE_KEY)


CATEGORY_OPTIONS = ["IT", "Maker Space", "Discard"]
LOCATION_BY_CATEGORY = {
    "IT": "IT Shop",
    "Maker Space": "Maker Space",
    "Discard": "N/A",
}
WEATHER_URL = (
    "https://api.open-meteo.com/v1/forecast"
    "?latitude=47.6062&longitude=-122.3321&current_weather=true"
)


def weather_code_to_text(code):
    if code is None:
        return "Unknown"
    if code == 0:
        return "Clear"
    if 1 <= code <= 3:
        return "Cloudy"
    if 45 <= code <= 48:
        return "Fog"
    if 51 <= code <= 67:
        return "Drizzle/Rain"
    if 71 <= code <= 77:
        return "Snow"
    if 80 <= code <= 82:
        return "Showers"
    if code == 95:
        return "Thunderstorm"
    return "Unknown"


def show_weather_widget():
    st.sidebar.subheader("Seattle Weather")

    try:
        response = requests.get(WEATHER_URL, timeout=10)
        assert response.status_code == 200, "Weather API returned non-200"

        data = response.json()
        assert "current_weather" in data, "Missing current_weather in response"

        current_weather = data["current_weather"]
        temperature = current_weather.get("temperature")
        weather_code = current_weather.get("weathercode")
        description = weather_code_to_text(weather_code)

        st.sidebar.write(f"{temperature} °C")
        st.sidebar.caption(description)
    except AssertionError as exc:
        st.sidebar.warning(str(exc))
    except Exception:
        st.sidebar.warning("Weather unavailable")


def clean_product_name(product_name):
    product_name = str(product_name)
    pipe_index = product_name.find("|")
    comma_index = product_name.find(",")
    split_points = [index for index in [pipe_index, comma_index] if index != -1]

    if split_points:
        product_name = product_name[: min(split_points)]

    return product_name.strip()[:40]


def make_processing_table(uploaded_df):
    return pd.DataFrame(
        {
            "original_name": uploaded_df["product_name"].astype(str),
            "clean_name": uploaded_df["product_name"].apply(clean_product_name),
            "quantity": uploaded_df["quantity"],
            "asset_tag_id": [
                f"{asset_id:08d}"
                for asset_id in range(10000001, 10000001 + len(uploaded_df))
            ],
            "category": "IT",
            "model_serial": "",
        }
    )


def add_locations(inventory_df):
    inventory_df = inventory_df.copy()
    inventory_df["location"] = inventory_df["category"].map(LOCATION_BY_CATEGORY).fillna("N/A")
    return inventory_df


def dataframe_to_records(inventory_df):
    records_df = add_locations(inventory_df)
    records_df = records_df.where(pd.notnull(records_df), None)
    return records_df.to_dict(orient="records")


def fetch_inventory(order_by_created_at=False):
    query = supabase.table("inventory_items").select("*")
    if order_by_created_at:
        query = query.order("created_at", desc=True)

    return query.execute().data


show_weather_widget()

st.title("GIX Inventory Pre-Processor")
st.caption(
    "Upload equipment return CSVs, clean item names, assign asset tags, and export rows for BluTally."
)

upload_tab, inventory_tab, export_tab = st.tabs(
    ["Upload & Process", "View Inventory", "Export"]
)


with upload_tab:
    st.subheader("Upload Equipment Return List")
    uploaded_file = st.file_uploader(
        "Upload a CSV file. Expected columns: product_name, quantity",
        type=["csv"],
    )

    if uploaded_file is not None:
        try:
            uploaded_df = pd.read_csv(uploaded_file)
        except Exception as exc:
            st.error(f"Could not read CSV: {exc}")
        else:
            required_columns = {"product_name", "quantity"}
            missing_columns = required_columns - set(uploaded_df.columns)

            if missing_columns:
                st.error(
                    "Missing required column(s): "
                    + ", ".join(sorted(missing_columns))
                )
            else:
                st.info(f"{len(uploaded_df)} row(s) detected.")

                processing_df = make_processing_table(uploaded_df)
                edited_df = st.data_editor(
                    processing_df,
                    use_container_width=True,
                    hide_index=True,
                    disabled=["original_name", "quantity"],
                    column_config={
                        "original_name": st.column_config.TextColumn("Original Name"),
                        "clean_name": st.column_config.TextColumn("Clean Name"),
                        "quantity": st.column_config.NumberColumn("Quantity"),
                        "asset_tag_id": st.column_config.TextColumn("Asset Tag ID"),
                        "category": st.column_config.SelectboxColumn(
                            "Category",
                            options=CATEGORY_OPTIONS,
                            required=True,
                        ),
                        "model_serial": st.column_config.TextColumn(
                            "Model/Serial Number"
                        ),
                    },
                )

                preview_df = add_locations(edited_df)
                st.caption("Location is automatically set from category.")
                st.dataframe(
                    preview_df[
                        [
                            "asset_tag_id",
                            "clean_name",
                            "category",
                            "location",
                            "model_serial",
                        ]
                    ],
                    use_container_width=True,
                    hide_index=True,
                )

                if st.button("Save to Supabase", type="primary"):
                    try:
                        records = dataframe_to_records(edited_df)
                        supabase.table("inventory_items").insert(records).execute()
                        st.success(f"Saved {len(records)} item(s) to Supabase.")
                    except Exception as exc:
                        st.error(f"Failed to save inventory items: {exc}")


with inventory_tab:
    st.subheader("Current Inventory")

    try:
        inventory_rows = fetch_inventory(order_by_created_at=True)
        inventory_df = pd.DataFrame(inventory_rows)
        st.metric("Total Items", len(inventory_df))
        st.dataframe(inventory_df, use_container_width=True, hide_index=True)
    except Exception as exc:
        st.error(f"Failed to fetch inventory items: {exc}")


with export_tab:
    st.subheader("Export for BluTally")

    try:
        inventory_rows = fetch_inventory()
        inventory_df = pd.DataFrame(inventory_rows)

        if inventory_df.empty:
            st.info("No inventory items available to export.")
        else:
            export_df = pd.DataFrame(
                {
                    "Asset Name": inventory_df.get("clean_name", ""),
                    "Asset Tag ID": inventory_df.get("asset_tag_id", ""),
                    "Status": "Available",
                    "Location": inventory_df.get("location", ""),
                    "Model/Serial Number": inventory_df.get("model_serial", ""),
                }
            )

            csv_buffer = StringIO()
            export_df.to_csv(csv_buffer, index=False)

            st.dataframe(export_df, use_container_width=True, hide_index=True)
            st.download_button(
                "Download BluTally CSV",
                data=csv_buffer.getvalue(),
                file_name="blutally_inventory_export.csv",
                mime="text/csv",
            )
    except Exception as exc:
        st.error(f"Failed to export inventory items: {exc}")
