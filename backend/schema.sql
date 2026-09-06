-- ============================================
-- TRAIN INFO FINDER - POSTGRESQL SCHEMA
-- ============================================


-- ------------------------
-- STATIONS TABLE
-- ------------------------

CREATE TABLE IF NOT EXISTS stations (
    code VARCHAR(20) PRIMARY KEY,
    name TEXT NOT NULL,
    lat DOUBLE PRECISION,
    lon DOUBLE PRECISION
);


-- ------------------------
-- TRAINS TABLE
-- ------------------------

CREATE TABLE IF NOT EXISTS trains (
    number VARCHAR(10) PRIMARY KEY,
    name TEXT NOT NULL,
    type VARCHAR(50),
    type_label TEXT,
    runs_days TEXT,

    source_code VARCHAR(20),
    source TEXT,

    dest_code VARCHAR(20),
    destination TEXT,

    distance_km NUMERIC(10, 2),
    travel_time VARCHAR(20),
    num_stops INTEGER
);


-- ------------------------
-- STOPS TABLE
-- ------------------------

CREATE TABLE IF NOT EXISTS stops (
    train_number VARCHAR(10) NOT NULL,
    seq INTEGER NOT NULL,

    station_code VARCHAR(20),
    station_name TEXT,

    day INTEGER,

    arrival VARCHAR(10),
    departure VARCHAR(10),

    halt_min NUMERIC(10, 2),
    distance_km NUMERIC(10, 2),

    PRIMARY KEY (train_number, seq),

    CONSTRAINT fk_stops_train
        FOREIGN KEY (train_number)
        REFERENCES trains(number)
        ON DELETE CASCADE
);


-- ============================================
-- INDEXES
-- ============================================

CREATE INDEX IF NOT EXISTS idx_stops_station_code
ON stops(station_code);

CREATE INDEX IF NOT EXISTS idx_stations_name
ON stations(name);

CREATE INDEX IF NOT EXISTS idx_trains_source_code
ON trains(source_code);

CREATE INDEX IF NOT EXISTS idx_trains_dest_code
ON trains(dest_code);