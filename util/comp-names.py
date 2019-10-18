# ------------------------------------------------ #
# Author: Brett Kurzawa                            #
# Date: 10/16/2019                                 #
# File description:                                #
#      Quick script to gather the names of comps   #
#      which have already been scraped. Purpose    #
#      is so that each time the scraper is run it  #
#      won't have to go through all of the data.   #
# ------------------------------------------------ #

import pandas as pd
import numpy as np

def main():
    """
    Load comps from all csv files, check for unique comp names,
    add all to a list, export as csv file of unique names
    """

    # Contains list of unique comp names
    unique_names = []

    # Names of files containing data
    filenames = ['boulder_results.csv', 'speed_results.csv', 'combined_results.csv', 'lead_results.csv']

    # Iterate through files and merge comp names into a list of unique names
    for filename in filenames:
        data_path = '~/projects/ifsc-scraper/data/'

        # Load file
        df = pd.read_csv(data_path+filename)

        # Get unique names from this file
        this_file_unique = df['Competition Title'].unique()

        # Merge unique names into overall list
        unique_names = list(set(unique_names).union(set(this_file_unique)))
    
    # Dataframe containing unique names
    name_df = pd.DataFrame(unique_names, columns=['Competition Title'])

    # Write unique names to csv
    name_df.to_csv('~/projects/ifsc-scraper/data/name_df.csv', index=False)

if __name__ == '__main__':
    main()