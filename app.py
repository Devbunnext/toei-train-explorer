import os, urllib.request, zipfile
import duckdb
import plotly.express as px
import streamlit as st

st.set_page_config(page_title="Toei Train Explorer", layout="wide")
st.markdown("""
<style>
#MainMenu {visibility: hidden;}
footer {visibility: hidden;}
[data-testid="stToolbar"] {display: none;}
</style>
""", unsafe_allow_html=True)
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

HOURS = [f"{h:02d}:00" for h in range(24)]

all_lines = sorted(df["line"].dropna().unique())
lines = st.sidebar.multiselect("Line", all_lines, default=all_lines)
start, end = st.sidebar.select_slider(
    "Time range", options=HOURS, value=(HOURS[0], HOURS[-1])
)
h_min, h_max = HOURS.index(start), HOURS.index(end)

f = df[df["line"].isin(lines) & df["hour"].between(h_min, h_max)]

if f.empty:
    st.info("Please select at least one line to display the data.")
    st.stop()

c1, c2, c3 = st.columns(3)
c1.metric("Total departures", f"{f['departures'].sum():,}")
c2.metric("Stations", f["station"].nunique())
peak = f.groupby("hour")["departures"].sum().idxmax()
c3.metric("Peak hour", f"{peak:02d}:00")

hourly = f.groupby("hour", as_index=False)["departures"].sum()
hourly["time"] = hourly["hour"].map(lambda h: f"{h:02d}:00")
st.plotly_chart(
    px.bar(hourly, x="time", y="departures", title="Departures by hour",
           category_orders={"time": HOURS}),
    use_container_width=True)

top = (f.groupby("station", as_index=False)["departures"].sum()
        .nlargest(15, "departures"))
st.plotly_chart(
    px.bar(top, x="departures", y="station", orientation="h",
           title="Top 15 stations by departures")
      .update_yaxes(autorange="reversed"),
    use_container_width=True)

heat = f.groupby(["line", "hour"], as_index=False)["departures"].sum()
heat["time"] = heat["hour"].map(lambda h: f"{h:02d}:00")
st.plotly_chart(
    px.density_heatmap(heat, x="time", y="line", z="departures",
                       title="Line × hour",
                       category_orders={"time": HOURS}),
    use_container_width=True)
