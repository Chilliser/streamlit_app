import os
import streamlit as st
import gdown
import json
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import numpy as np
import folium
from scipy.interpolate import griddata
import matplotlib.pyplot as plt
from matplotlib.colors import ListedColormap, BoundaryNorm
from streamlit_folium import st_folium

# ดึงไฟล์ JSON credentials
url = 'https://drive.google.com/uc?id=1q8-atFJitP9sNNpNS04-IeMd0rZzuHzo'
output = 'creds.json'
gdown.download(url, output, quiet=False)

# โหลด JSON credentials
with open(output, 'r') as file:
    creds_dict = json.load(file)

# ตั้งค่า Google Sheets API
scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
client = gspread.authorize(creds)

# เปิดสเปรดชีต
spreadsheet_name = 'RealAir'
spreadsheet = client.open(spreadsheet_name)
worksheet = spreadsheet.sheet1

# กำหนดค่าคงที่สำหรับพิกัดและขนาดกริด
latitude_center = 14.8818
longitude_center = 102.0188
grid_size_meters = 500

# ฟังก์ชั่นแปลงจาก meter เป็น degree
def meter_to_degree(meter):
    return meter / 111131

# ขยายช่วงพิกัด latitude และ longitude เพื่อครอบคลุม มทส.
latitude_range = (latitude_center - 0.027, latitude_center + 0.025)
longitude_range = (longitude_center - 0.024, longitude_center + 0.022)

# สร้างตารางพิกัด
latitudes = np.arange(latitude_range[0], latitude_range[1], meter_to_degree(grid_size_meters))
longitudes = np.arange(longitude_range[0], longitude_range[1], meter_to_degree(grid_size_meters))

# กำหนดตำแหน่งเซ็นเซอร์
sensor_locations = {}
index = 1
for lat in latitudes:
    for lon in longitudes:
        sensor_locations[f'Sensor{index}'] = [lat, lon]
        index += 1

# กำหนดเซ็นเซอร์ที่ต้องการแสดงผล
selected_sensors = list(range(21, 23)) + list(range(30, 34)) + list(range(39, 45)) + \
                   list(range(48, 56)) + list(range(58, 64)) + list(range(67, 75)) + \
                   list(range(78, 85)) + list(range(89, 95)) + list(range(100, 106)) + \
                   list(range(113, 116))

# ลบเซ็นเซอร์ที่ไม่อยู่ในรายการ selected_sensors
sensor_locations = {key: value for key, value in sensor_locations.items() if int(key[6:]) in selected_sensors}

# สร้างรายการเซ็นเซอร์ที่ต้องการดึงข้อมูล
sensor_cells = {
    'Sensor21': 'E4', 'Sensor22': 'E5', 'Sensor30': 'E6', 'Sensor31': 'E7',
    'Sensor32': 'E3', 'Sensor33': 'E8', 'Sensor39': 'E9', 'Sensor40': 'E10',
    'Sensor41': 'E11', 'Sensor42': 'E12', 'Sensor43': 'E13', 'Sensor44': 'E14',
    'Sensor48': 'E15', 'Sensor49': 'E16', 'Sensor50': 'E17', 'Sensor51': 'E18',
    'Sensor52': 'E19', 'Sensor53': 'E20', 'Sensor54': 'E21', 'Sensor55': 'E22',
    'Sensor58': 'E23', 'Sensor59': 'E24', 'Sensor60': 'E25', 'Sensor61': 'E26',
    'Sensor62': 'E27', 'Sensor63': 'E28', 'Sensor67': 'E29', 'Sensor68': 'E30',
    'Sensor69': 'E31', 'Sensor70': 'E32', 'Sensor71': 'E33', 'Sensor72': 'E2',
    'Sensor73': 'E34', 'Sensor74': 'E35', 'Sensor78': 'E36', 'Sensor79': 'E37',
    'Sensor80': 'E38', 'Sensor81': 'E39', 'Sensor82': 'E40', 'Sensor83': 'E41',
    'Sensor84': 'E42', 'Sensor89': 'E43', 'Sensor90': 'E44', 'Sensor91': 'E45',
    'Sensor92': 'E46', 'Sensor93': 'E47', 'Sensor94': 'E48', 'Sensor100': 'E49',
    'Sensor101': 'E50', 'Sensor102': 'E51', 'Sensor103': 'E52', 'Sensor104': 'E53',
    'Sensor105': 'E54', 'Sensor113': 'E55', 'Sensor114': 'E56', 'Sensor115': 'E57'
}

# ดึงข้อมูลจากช่วงของเซลล์ทั้งหมดในครั้งเดียว
cell_range = worksheet.range('E2:E57')

# จัดการข้อมูลให้อยู่ในรูป dictionary
pm25_values = {}
for sensor, cell in sensor_cells.items():
    cell_index = int(cell[1:]) - 2
    pm25_values[sensor] = float(cell_range[cell_index].value)

# แปลงข้อมูลเป็น numpy arrays
sensor_coords = np.array(list(sensor_locations.values()))
sensor_values = np.array(list(pm25_values.values()))

# สร้างกริดที่ละเอียดขึ้น
grid_lat, grid_lon = np.mgrid[
    latitude_range[0]:latitude_range[1]:100j,
    longitude_range[0]:longitude_range[1]:100j
]

# ใช้การสอดแทรกเพื่อสร้างพื้นผิว PM2.5
grid_z = griddata(sensor_coords, sensor_values, (grid_lat, grid_lon), method='cubic')

# สร้าง contour plot
def generate_contour_plot(grid_lat, grid_lon, grid_z, output_filename):
    fig, ax = plt.subplots(figsize=(12, 12))  # ลดขนาด
    levels = [0, 15, 25, 37.5, 75, 150]
    colors = ['#00BFFF', '#00FF00', '#FFFF00', '#FFA500', '#FF0000']
    cmap = ListedColormap(colors)
    norm = BoundaryNorm(levels, ncolors=cmap.N, clip=True)

    contour = ax.contourf(grid_lon, grid_lat, grid_z, levels=levels, cmap=cmap, norm=norm, alpha=0.6)
    ax.axis('off')

    plt.savefig(output_filename, format='png', bbox_inches='tight', pad_inches=0, transparent=True)
    plt.close(fig)

# Streamlit Section
st.title('PM2.5 Contour and Sensor Map')

contour_img_filename = 'contour_plot.png'
generate_contour_plot(grid_lat, grid_lon, grid_z, contour_img_filename)

# สร้างแผนที่ด้วย folium
m = folium.Map(location=[latitude_center, longitude_center], zoom_start=14)
img_overlay = folium.raster_layers.ImageOverlay(
    image=contour_img_filename,
    bounds=[[latitude_range[0], longitude_range[0]], [latitude_range[1], longitude_range[1]]],
    opacity=0.6,
)
img_overlay.add_to(m)

# แสดงแผนที่
st_data = st_folium(m, width=725)

# เพิ่มข้อมูลเซ็นเซอร์
for sensor_id, coords in sensor_locations.items():
    folium.Marker(
        location=coords,
        popup=f'{sensor_id}: PM2.5={pm25_values[sensor_id]}',
        icon=folium.Icon(color='blue', icon='info-sign')
    ).add_to(m)
