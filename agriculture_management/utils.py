# -*- coding: utf-8 -*-
"""OpenWeatherMapAPI.ipynb

Automatically generated by Colaboratory.

Original file is located at
    https://colab.research.google.com/drive/1P2n4LdriXp6Imm9g5fE7Rvm5hc0ySXif
"""

import requests
import pandas as pd
from geopy.geocoders import Nominatim
from geopy.extra.rate_limiter import RateLimiter

"""# Geo geographical coordinates using OSM Nominatim service

More details on using Nominatim API

https://nominatim.org/release-docs/develop/api/Search/
"""

cities = [
    ["Kyiv", "Ukraine"],
    ["Warsaw", "Poland"],
    ["Berlin", "Germany"],
    ["London", "UK"],
    ["Madrid", "Spain"],
    ["Paris", "France"],
    ["Rome", "Italy"],
    ["Prague", "Czechia"],
    ["Istanbul", "Turkey"],
    ["Stockholm", "Sweden"],
    ["Sofia", "Bulgaria"],
    ["Bucharest", "Romania"],
    ["Zurich", "Switzerland"],
]

df = pd.DataFrame(cities, columns=["city", "country"])

locator = Nominatim(user_agent="myGeocoder")
geocode = RateLimiter(locator.geocode, min_delay_seconds=.1)

def get_coordinates(city, country):
    response = geocode(query={"city": city, "country": country})
    return {
        "latitude": response.latitude,
        "longitude": response.longitude
    }

df_coordinates = df.apply(lambda x: get_coordinates(x.city, x.country), axis=1)
df = pd.concat([df, pd.json_normalize(df_coordinates)], axis=1)

df

"""# Get weather data

https://openweathermap.org/api/one-call-3

Go to https://home.openweathermap.org/api_keys to get Openweathermap API key
"""

from getpass import getpass
openweathermap_api_key = "81b09706b0075c212be5ebfb9d69a915"

import datetime

def get_weather(row):

    owm_url = f"https://api.openweathermap.org/data/2.5/weather?lat={row.latitude}&lon={row.longitude}&appid={openweathermap_api_key}"
    owm_response = requests.get(owm_url)
    owm_response_json = owm_response.json()
    sunset_utc = datetime.datetime.fromtimestamp(owm_response_json["sys"]["sunset"])
    return {
        "temp": owm_response_json["main"]["temp"] - 273.15,
        "description": owm_response_json["weather"][0]["description"],
        "icon": owm_response_json["weather"][0]["icon"],
        "sunset_utc": sunset_utc,
        "sunset_local": sunset_utc + datetime.timedelta(seconds=owm_response_json["timezone"])
    }

df_weather = df.apply(lambda x: get_weather(x), axis=1)
df = pd.concat([df, pd.json_normalize(df_weather)], axis=1)

df

# Commented out IPython magic to ensure Python compatibility.
try:
    import geopandas as gpd
except ModuleNotFoundError:
    if 'google.colab' in str(get_ipython()):
#     %pip install geopandas
        import geopandas as gpd

gdf = gpd.GeoDataFrame(df, geometry=gpd.points_from_xy(df.longitude, df.latitude), crs=4326)

# Commented out IPython magic to ensure Python compatibility.
try:
    import contextily as ctx
except ModuleNotFoundError:
    if 'google.colab' in str(get_ipython()):
#     %pip install contextily
        import contextily as ctx

from skimage import io
import matplotlib.pyplot as plt
from matplotlib.offsetbox import AnnotationBbox, OffsetImage

# plot city location marker
ax = gdf.to_crs(epsg=3857).plot(figsize=(12,8), color="black")

# add weather icon
def add_icon(row):
    img = io.imread(f"https://openweathermap.org/img/wn/{row.icon}@2x.png")
    img_offset = OffsetImage(img, zoom=.4, alpha=1, )
    ab = AnnotationBbox(img_offset, [row.geometry.x+150000, row.geometry.y-110000], frameon=False)
    ax.add_artist(ab)

gdf.to_crs(epsg=3857).apply(add_icon, axis=1)

# add city name label
gdf.to_crs(epsg=3857).apply(lambda x: ax.annotate(text=f"{x.city}  ", fontsize=10, color="black", xy=x.geometry.centroid.coords[0], ha='right'), axis=1);

# add temperature
gdf.to_crs(epsg=3857).apply(lambda x: ax.annotate(text=f" {round(x.temp)}°", fontsize=15, color="black", xy=x.geometry.centroid.coords[0], ha='left'), axis=1);

# add margins
xmin, ymin, xmax, ymax = gdf.to_crs(epsg=3857).total_bounds
margin_y = .2
margin_x = .2
y_margin = (ymax - ymin) * margin_y
x_margin = (xmax - xmin) * margin_x

ax.set_xlim(xmin - x_margin, xmax + x_margin)
ax.set_ylim(ymin - y_margin, ymax + y_margin)

# add basemap
ctx.add_basemap(ax, source=ctx.providers.Stamen.Watercolor)

ax.set_axis_off()