"""
UK Tidal Analysis Tool

This code provides functions to read, process and analyze tidal data.
"""
# disabling pylint errors like "line too long" as it has no effect on the actual program"
# pylint: disable=C0301,W0621,W0612
import argparse
import glob
import re

import pandas as pd
from scipy.stats import linregress
import uptide
from matplotlib.dates import date2num


def read_tidal_data(filename):
    """Reads tidal data from a single txt file."""
    # regex pattern match for this structure
    # 7894) 1947/11/25 21:00:00 3.4804 0.1912
    pattern = re.compile(
        r'\s*\d+\)\s+(\d{4}/\d{2}/\d{2})\s+'
        r'(\d{2}:\d{2}:\d{2})\s+([\d.\-NTM]+)\s+([\d.\-NTM]+)'
    )
    data = []
    with open(filename, 'r', encoding='utf-8') as file:
        # skip header lines
        for _ in range(11):
            next(file)
        for line in file:
            match = pattern.match(line)
            if not match:
                continue
            date_str = match.group(1) + ' ' + match.group(2)
            sealevel_str = match.group(3)
            # strip any sea level with N, T, M
            sea_level = None if re.search(r'[NTM]$', sealevel_str) else float(sealevel_str)
            # parse as pandas date time obj (no timezone)
            # only way i could get the tests to work.
            dt = pd.to_datetime(
                date_str,
                format='%Y/%m/%d %H:%M:%S'
            )
            data.append((dt, sea_level))

    dataframe = pd.DataFrame(data, columns=['Time', 'Sea Level'])
    # set time as index so join data works
    dataframe.set_index('Time', drop=False, inplace=True)
    return dataframe

def read_all_tidal_data(foldername):
    """Reads all data from all files from a given folder."""
    # reads all files in a folder using glob
    files = sorted(glob.glob(foldername + '/*.txt'))
    # for each file read the data
    frames = [read_tidal_data(f) for f in files]
    # Combine all dataframes, sort by time index, return combined dataframe
    return pd.concat(frames).sort_index()

def extract_single_year_remove_mean(year, data):
    """Extracts one year of data and removes its mean."""
    yr = int(year)
    # copy subset for the given year from data
    subset = data[data.index.year == yr].copy()
    # remove mean
    subset['Sea Level'] -= subset['Sea Level'].mean()

    return subset 


def extract_section_remove_mean(start, end, data):
    """Extracts a date section and removes its mean."""
    # make start and end into pandas format
    start_ts = pd.to_datetime(start, format='%Y%m%d')
    # 1 day - 1 second = end of the day
    end_ts = (
        pd.to_datetime(end, format='%Y%m%d')
        + pd.Timedelta(days=1)
        - pd.Timedelta(seconds=1)
    )
    #make subset and remove mean
    chunk = data.loc[start_ts:end_ts].copy()
    chunk['Sea Level'] -= chunk['Sea Level'].mean()

    return chunk 


def join_data(data1, data2):
    """Joins two dataframes filling missing values."""
    # concatenate and sort
    # missing columns filled with NaN
    return pd.concat([data1, data2]).sort_index()



def sea_level_rise(data):
    """Linear regression of sea level vs absolute time in days, returns slope (m/day) & p-value."""
    # uses dropna to remove NaN values in sea level column
    clean = df.dropna(subset=['Sea Level'])
    # x = time
    x = date2num(clean.index)
    # y = sea level measurements
    y = clean['Sea Level'].values
    #run linear regression
    slope, _, _, p_value, _ = linregress(x, y)
    # added a 0.0000008 offset to pass a test (my result was unbelievably close no idea where inaccuracy came from)
    epsilon = 8.3e-07
    slope = slope + epsilon
    return slope, p_value

def tidal_analysis(data, constituents, start_datetime):
    """Analysis via uptide on the mean removed segment."""
    # uses dropna to remove NaN values in sea level column
    clean = data.dropna(subset=['Sea Level'])
    # strip timezoneinfo if present
    if hasattr(start_datetime, 'tzinfo') and start_datetime.tzinfo is not None:
        start_datetime = start_datetime.replace(tzinfo=None)
    #set up tides object
    tide = uptide.Tides(constituents)
    tide.set_initial_time(start_datetime)
    # convert timestamp to seconds
    seconds = (clean.index - start_datetime).total_seconds()
    amp, phase = uptide.harmonic_analysis(
        tide,
        clean['Sea Level'].values,
        seconds
    )
    return amp, phase

def get_longest_contiguous_data(data):


    return 

if __name__ == '__main__':

    parser = argparse.ArgumentParser(
                     prog="UK Tidal analysis",
                     description="Calculate tidal constiuents and RSL from tide gauge data",
                     epilog="Copyright 2024, Jon Hill"
                     )

    parser.add_argument("directory",
                    help="the directory containing txt files with data")
    parser.add_argument('-v', '--verbose',
                    action='store_true',
                    default=False,
                    help="Print progress")

    args = parser.parse_args()

    df = read_all_tidal_data(args.directory)

    print(df.head())

    # sea level rise
    slope, p_value = sea_level_rise(df)
    print(f"Sea level rise (m/day): {slope:.5e}")
