from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import pandas as pd

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

trains = pd.read_csv("data/trains.csv")
stops = pd.read_csv("data/stops.csv")
stations = pd.read_csv("data/stations.csv")


@app.get("/")
def home():
    return {
        "message": "Train Info Finder API is running"
    }


@app.get("/train/{train_number}")
def get_train(train_number: str):

    result = trains[
        trains["number"].astype(str) == train_number
    ]

    if result.empty:
        raise HTTPException(
            status_code=404,
            detail="Train not found"
        )

    train = result.iloc[0]

    route = stops[
        stops["train_number"].astype(str) == train_number
    ].sort_values("seq")

    route_data = []

    for _, stop in route.iterrows():

        route_data.append({
            "seq": int(stop["seq"]) if pd.notna(stop["seq"]) else None,

            "station_code": (
                str(stop["station_code"])
                if pd.notna(stop["station_code"])
                else None
            ),

            "station_name": (
                str(stop["station_name"])
                if pd.notna(stop["station_name"])
                else None
            ),

            "arrival": (
                str(stop["arrival"])
                if pd.notna(stop["arrival"])
                else None
            ),

            "departure": (
                str(stop["departure"])
                if pd.notna(stop["departure"])
                else None
            ),

            "day": (
                int(stop["day"])
                if pd.notna(stop["day"])
                else None
            ),

            "distance_km": (
                float(stop["distance_km"])
                if pd.notna(stop["distance_km"])
                else None
            )
        })

    return {
        "number": str(train["number"]),

        "name": (
            str(train["name"])
            if pd.notna(train["name"])
            else None
        ),

        "type": (
            str(train["type_label"])
            if pd.notna(train["type_label"])
            else None
        ),

        "source": (
            str(train["source"])
            if pd.notna(train["source"])
            else None
        ),

        "destination": (
            str(train["destination"])
            if pd.notna(train["destination"])
            else None
        ),

        "runs_days": (
            str(train["runs_days"])
            if pd.notna(train["runs_days"])
            else None
        ),

        "distance_km": (
            float(train["distance_km"])
            if pd.notna(train["distance_km"])
            else None
        ),

        "travel_time": (
            str(train["travel_time"])
            if pd.notna(train["travel_time"])
            else None
        ),

        "num_stops": (
            int(train["num_stops"])
            if pd.notna(train["num_stops"])
            else None
        ),

        "route": route_data
    }

@app.get("/stations/search")
def search_stations(q: str):

    q = q.strip().lower()

    if len(q) < 1:
        return []

    results = stations[
        stations["name"].astype(str).str.lower().str.contains(q, na=False)
        |
        stations["code"].astype(str).str.lower().str.contains(q, na=False)
    ].head(10)

    return [
        {
            "code": str(row["code"]),
            "name": str(row["name"])
        }
        for _, row in results.iterrows()
    ]


@app.get("/station/{station_code}")
def get_station(station_code: str):

    station_code = station_code.strip().upper()

    station_result = stations[
        stations["code"].astype(str).str.upper() == station_code
    ]

    if station_result.empty:
        raise HTTPException(
            status_code=404,
            detail="Station not found"
        )

    station = station_result.iloc[0]

    station_stops = stops[
        stops["station_code"].astype(str).str.upper() == station_code
    ].drop_duplicates(subset="train_number")

    trains_here = []

    for _, stop in station_stops.iterrows():

        number = str(stop["train_number"])

        train_result = trains[
            trains["number"].astype(str) == number
        ]

        if train_result.empty:
            continue

        train = train_result.iloc[0]

        trains_here.append({
            "number": number,
            "name": str(train["name"]),
            "type": str(train["type_label"]),
            "source": str(train["source"]),
            "destination": str(train["destination"]),

            "arrival": (
                str(stop["arrival"])
                if pd.notna(stop["arrival"])
                else None
            ),

            "departure": (
                str(stop["departure"])
                if pd.notna(stop["departure"])
                else None
            ),

            "day": (
                int(stop["day"])
                if pd.notna(stop["day"])
                else None
            )
        })

    return {
        "station_code": str(station["code"]),
        "station_name": str(station["name"]),
        "train_count": len(trains_here),
        "trains": trains_here
    }