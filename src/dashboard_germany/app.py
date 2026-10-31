
import streamlit as st
import pandas as pd
import plotly.express as px

from api.eurostat_client import get_gdp_data
from config.regions import get_region_group, EAST_GERMANY, BERLIN


st.set_page_config(
    page_title="Germany: East vs West",
    page_icon="🇩🇪",
    layout="wide",
)

st.title("Germany: East vs West")
st.caption("Economic and Social Analysis")

st.sidebar.header("Filters")

@st.cache_data(ttl=3600)
def load_data():
    return get_gdp_data()


try:
    with st.spinner("Loading Eurostat data..."):
        df = load_data()

except Exception as error:
    st.error(f"Failed to load data: {error}")
    st.stop()


df["year"] = pd.to_numeric(df["time"], errors="coerce")
df["value"] = pd.to_numeric(df["value"], errors="coerce")

df["group"] = df["geo"].apply(get_region_group)

df = df[
    df["geo"].str.startswith("DE")
    & (df["geo"].str.len() == 4)
    & (df["geo"] != BERLIN)
    & df["group"].notna()
    & df["value"].notna()
].copy()

if df.empty:
    st.warning("No German regional data available.")
    st.stop()


years = sorted(df["year"].dropna().unique())

selected_year = st.sidebar.selectbox(
    "Year",
    years,
    index=len(years) - 1,
)

selected_regions = st.sidebar.multiselect(
    "Regions",
    sorted(df["geo"].unique()),
    default=sorted(df["geo"].unique()),
)

filtered_df = df[
    (df["year"] == selected_year)
    & df["geo"].isin(selected_regions)
].copy()

east = filtered_df[filtered_df["group"] == "East"]["value"]
west = filtered_df[filtered_df["group"] == "West"]["value"]

col1, col2, col3 = st.columns(3)

col1.metric(
    "East Germany - median GDP per capita",
    f"{east.median():,.0f}" if not east.empty else "N/A",
)

col2.metric(
    "West Germany - median GDP per capita",
    f"{west.median():,.0f}" if not west.empty else "N/A",
)

difference = (
    (east.median() / west.median() - 1) * 100
    if not east.empty and not west.empty and west.median() != 0
    else None
)

col3.metric(
    "East vs West difference",
    f"{difference:+.1f}%" if difference is not None else "N/A",
)

st.divider()

st.subheader(f"GDP per capita by region - {selected_year}")

sorted_df = filtered_df.sort_values("value")

fig = px.bar(
    sorted_df,
    x="value",
    y="geo",
    color="group",
    orientation="h",
    hover_data=["geo_label"],
    color_discrete_map={
        "East": "#D96B6B",
        "West": "#5B8DB8",
    },
    labels={
        "value": "GDP per capita (PPS)",
        "geo": "Region",
        "group": "Historical region",
    },
)

fig.update_layout(
    yaxis={
        "categoryorder": "array",
        "categoryarray": sorted_df["geo"].tolist(),
    }
)

st.plotly_chart(fig, use_container_width=True)