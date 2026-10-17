!pip install duckdb plotly -q
import urllib.request, zipfile, duckdb

url = "https://api-public.odpt.org/api/v4/files/Toei/data/Toei-Train-GTFS.zip"
urllib.request.urlretrieve(url, "toei_train.zip")
zipfile.ZipFile("toei_train.zip").extractall("toei_train")

duckdb.sql("SELECT * FROM read_csv('toei_train/stops.txt') ").show()

import plotly.express as px

# 1) عدد القطارات في كل ساعة
hourly = duckdb.sql("""
  SELECT
    CAST(split_part(departure_time, ':', 1) AS INT) % 24 AS hour,
    COUNT(*) AS departures
  FROM read_csv('toei_train/stop_times.txt')
  GROUP BY hour
  ORDER BY hour
""").df()

print(hourly)

# 2) الرسم
px.bar(hourly, x="hour", y="departures",
       title="Toei trains: departures by hour").show()
