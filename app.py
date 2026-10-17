import os, urllib.request, zipfile
import duckdb
import plotly.express as px
import streamlit as st

st.set_page_config(page_title="Toei Train Explorer", layout="wide")
URL = "https://api-public.odpt.org/api/v4/files/Toei/data/Toei-Train-GTFS.zip"

@st.cache_data
def load():
    if not os.path.exists("gtfs"):
        urllib.request.urlretrieve(URL, "toei.zip")
        zipfile.ZipFile("toei.zip").extractall("gtfs")
    return duckdb.sql("""
      SELECT
        r.route_long_name AS line,
        s.stop_name AS station,
        CAST(split_part(st.departure_time, ':', 1) AS INT) % 24 AS hour,
        COUNT(*) AS departures
      FROM read_csv('gtfs/stop_times.txt') st
      JOIN read_csv('gtfs/trips.txt') t USING (trip_id)
      JOIN read_csv('gtfs/routes.txt') r USING (route_id)
      JOIN read_csv('gtfs/stops.txt') s USING (stop_id)
      GROUP BY line, station, hour
    """).df()

df = load()

st.title("🚇 Toei Train Service Explorer (Tokyo)")
st.caption("Source: ODPT, GTFS timetable data (CC-BY-4.0)")

all_lines = sorted(df["line"].dropna().unique())
lines = st.sidebar.multiselect("Line", all_lines, default=all_lines)
h_min, h_max = st.sidebar.slider("Hour range", 0, 23, (0, 23))

f = df[df["line"].isin(lines) & df["hour"].between(h_min, h_max)]

c1, c2, c3 = st.columns(3)
c1.metric("Total departures", f"{f['departures'].sum():,}")
c2.metric("Stations", f["station"].nunique())
peak = f.groupby("hour")["departures"].sum().idxmax()
c3.metric("Peak hour", f"{peak}:00")

hourly = f.groupby("hour", as_index=False)["departures"].sum()
st.plotly_chart(px.bar(hourly, x="hour", y="departures",
                       title="Departures by hour"), use_container_width=True)

top = (f.groupby("station", as_index=False)["departures"].sum()
        .nlargest(15, "departures"))
st.plotly_chart(px.bar(top, x="departures", y="station", orientation="h",
                       title="Top 15 stations by departures")
                  .update_yaxes(autorange="reversed"), use_container_width=True)

heat = f.groupby(["line", "hour"], as_index=False)["departures"].sum()
st.plotly_chart(px.density_heatmap(heat, x="hour", y="line", z="departures",
                                   title="Line × hour"), use_container_width=True)
