import pandas as pd

# Load datasets
trains = pd.read_csv("data/trains.csv")
stops = pd.read_csv("data/stops.csv")
stations = pd.read_csv("data/stations.csv")

print("========== TRAIN INFO FINDER ==========")
print("1. Search by Train Number")
print("2. Search by Station Code")

choice = input("\nChoose an option (1 or 2): ").strip()


# ---------------------------------------------------
# OPTION 1: SEARCH BY TRAIN NUMBER
# ---------------------------------------------------

if choice == "1":

    train_number = input("\nEnter train number: ").strip()

    result = trains[
        trains["number"].astype(str) == train_number
    ]

    if result.empty:
        print("\nTrain not found.")

    else:
        train = result.iloc[0]

        print("\n========== TRAIN INFORMATION ==========")

        print("Train Number:", train["number"])
        print("Train Name:", train["name"])
        print("Type:", train["type_label"])
        print("Source:", train["source"])
        print("Destination:", train["destination"])
        print("Running Days:", train["runs_days"])
        print("Distance:", train["distance_km"], "km")
        print("Travel Time:", train["travel_time"])
        print("Number of Stops:", train["num_stops"])

        route = stops[
            stops["train_number"].astype(str) == train_number
        ]

        route = route.sort_values("seq")

        print("\n========== FULL ROUTE ==========")

        if route.empty:
            print("Route information not found.")

        else:

            for _, stop in route.iterrows():

                print(
                    f"{stop['seq']}. "
                    f"{stop['station_name']} "
                    f"({stop['station_code']}) | "
                    f"Arrival: {stop['arrival']} | "
                    f"Departure: {stop['departure']} | "
                    f"Day: {stop['day']} | "
                    f"Distance: {stop['distance_km']} km"
                )


# ---------------------------------------------------
# OPTION 2: SEARCH BY STATION CODE
# ---------------------------------------------------

elif choice == "2":

    station_code = input(
        "\nEnter station code: "
    ).strip().upper()

    station_result = stations[
        stations["code"].astype(str).str.upper()
        == station_code
    ]

    if station_result.empty:

        print("\nStation not found.")

    else:

        station = station_result.iloc[0]

        print("\n========== STATION INFORMATION ==========")

        print("Station Code:", station["code"])
        print("Station Name:", station["name"])

        station_stops = stops[
            stops["station_code"]
            .astype(str)
            .str.upper()
            == station_code
        ]

        print("\n========== TRAINS STOPPING HERE ==========")

        if station_stops.empty:

            print("No trains found.")

        else:

            # Remove duplicate train numbers
            station_stops = station_stops.drop_duplicates(
                subset="train_number"
            )

            for _, stop in station_stops.iterrows():

                train_number = str(
                    stop["train_number"]
                )

                train_result = trains[
                    trains["number"].astype(str)
                    == train_number
                ]

                if not train_result.empty:

                    train = train_result.iloc[0]

                    print(
                        f"{train_number} - "
                        f"{train['name']} | "
                        f"Arrival: {stop['arrival']} | "
                        f"Departure: {stop['departure']}"
                    )


else:

    print("\nInvalid option.")