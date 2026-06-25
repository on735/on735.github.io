from datetime import date, timedelta
from garminconnect import Garmin
import json
import os

EMAIL = os.environ["GARMIN_EMAIL"]
PASSWORD = os.environ["GARMIN_PASSWORD"]

client = Garmin(EMAIL, PASSWORD)
client.login()

end_date = date.today()
start_date = end_date - timedelta(days=365)

activities = client.get_activities_by_date(
    start_date.isoformat(),
    end_date.isoformat()
)

daily = {}

for activity in activities:
    activity_type = activity.get("activityType", {}).get("typeKey", "")

    if activity_type != "cycling":
        continue

    start_time = activity.get("startTimeLocal")
    activity_date = start_time[:10]

    distance_km = activity.get("distance", 0) / 1000
    max_speed_kmh = activity.get("maxSpeed", 0) * 3.6
    avg_speed_kmh = activity.get("averageSpeed", 0) * 3.6
    elapsed_seconds = activity.get("elapsedDuration", 0)

    if activity_date not in daily:
        daily[activity_date] = {
            "date": activity_date,
            "distanceKm": 0,
            "maxSpeedKmh": 0,
            "avgSpeedKmhTotal": 0,
            "activityCount": 0,
            "elapsedSeconds": 0
        }

    daily[activity_date]["distanceKm"] += distance_km
    daily[activity_date]["maxSpeedKmh"] = max(
        daily[activity_date]["maxSpeedKmh"],
        max_speed_kmh
    )
    daily[activity_date]["avgSpeedKmhTotal"] += avg_speed_kmh
    daily[activity_date]["activityCount"] += 1
    daily[activity_date]["elapsedSeconds"] += elapsed_seconds

if len(daily) == 0:
    raise Exception("No ride data found. Stop update to avoid overwriting rides.json.")

first_day = min(date.fromisoformat(d) for d in daily.keys())
current_day = first_day

while current_day <= end_date:
    key = current_day.isoformat()

    if key not in daily:
        daily[key] = {
            "date": key,
            "distanceKm": 0,
            "maxSpeedKmh": 0,
            "avgSpeedKmhTotal": 0,
            "activityCount": 0
            "elapsedSeconds": 0
        }

    current_day += timedelta(days=1)

rides = []

for item in daily.values():
    avg_speed = (
        item["avgSpeedKmhTotal"] / item["activityCount"]
        if item["activityCount"] > 0
        else 0
    )

    rides.append({
        "date": item["date"],
        "distanceKm": round(item["distanceKm"], 2),
        "maxSpeedKmh": round(item["maxSpeedKmh"], 1),
        "avgSpeedKmh": round(avg_speed, 1)
        "elapsedSeconds": round(item["elapsedSeconds"])
    })

rides.sort(key=lambda x: x["date"])

if len(rides) == 0:
    raise Exception("No ride data found. Stop update to avoid overwriting rides.json.")

output = {
    "updatedAt": f"{date.today().isoformat()}T07:35:00+09:00",
    "rides": rides
}

data_dir = os.path.join(os.path.dirname(__file__), "data")
os.makedirs(data_dir, exist_ok=True)

rides_path = os.path.join(data_dir, "rides.json")

with open(rides_path, "w", encoding="utf-8") as f:
    json.dump(output, f, indent=2, ensure_ascii=False)

print("data/rides.json updated")
print(json.dumps(output, indent=2, ensure_ascii=False))

import subprocess

subprocess.run(["git", "add", "data/rides.json"], check=True)
subprocess.run(["git", "commit", "-m", "Daily ride update"], check=False)
subprocess.run(["git", "push"], check=True)

print("GitHub pushed")
