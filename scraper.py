from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException
import pandas as pd
import numpy as np
import time

class IFSCScraper():
    """
    Define a class for the scraper that will be used to gather data from the IFSC website
    (ifsc-climbing.org)
    Includes methods that allow for scraping different pages and different information
    """

    def __init__(self, debug=False):
        """
        Initialize a scraper object with its own browser instance
        Input:
            debug - Indicates whether this is a debug instance for quicker development
        """

        self.debug = debug

        # Add incognito arg to webdriver
        option = webdriver.ChromeOptions()
        option.add_argument(" — incognito")

        # Create new instance of Chrome
        self.browser = webdriver.Chrome(options=option)

        time.sleep(1)


    def get_last_result_html(self):
        """
        Returns the html for the world competition last result page
        We will use this page to find more detailed information about recent competitions
        input:
            N/A
        output:
            html of the world competition last result page
        """

        # Page url
        url = 'https://www.ifsc-climbing.org/index.php/world-competition/last-result'

        self.load_page(url)


    def get_comp_links(self):
        """
        Parse the world-competition/last-result page to find and return comp names, dates, and links
        input:
            N/A
        output:
            List of touples containing comp names, dates, and url strings for each competition result page
        """

        # Page url
        url = 'https://www.ifsc-climbing.org/index.php/world-competition/last-result'

        self.load_page(url)

        comp_list = self.browser.find_elements_by_xpath("//select[@class='compChooser']")


        # List of comp names
        comp_list = [x.find_elements_by_tag_name('option') for x in comp_list]
        comp_list = comp_list[0]
        comp_names = [x.text for x in comp_list]
        
        # List of comp dates
        comp_dates = [x.get_attribute('title') for x in comp_list]

        # List of links to comps
        comp_links = [x.get_attribute('value') for x in comp_list]
        comp_links = [url + '#!comp=' + x for x in comp_links]
        

        return [(name, date, link) for name, date, link in zip(comp_names, comp_dates, comp_links)]

    def get_complete_result_links(self, comp_info):
        """
        Given the list of competitions, get links to the complete results for each subcategory in the comp
        input:
            comp_info: List of touples of comp names, dates, and links to page for comp results
        output:
            List of tuples giving comp name, date, subcategory name, and url to full results
            for that subcategory
        """

        if self.debug:
            limit = 3
            curr = 0

        # Hold new comp info
        new_info = []

        # Iterate through comps and visit each link
        for comp in comp_info:
            # Extract link
            comp_link = comp[-1]
            
            self.load_page(comp_link)

            # List of subcategories of competitions
            cat_list = self.browser.find_elements_by_xpath("//th[@colspan='4']")
            temp = [x.find_elements_by_tag_name('a') for x in cat_list]
            cat_list = [x.text for x in cat_list]

            # List of links to subcategories
            cat_links = [x[0].get_attribute('href') for x in temp]

            # Package info as tuples
            new_tuple = [((name, link),) for name, link in zip(cat_list, cat_links)]

            # Add tuples to current info
            for tup in new_tuple:
                comp += tup

            new_info.append(comp)

            if self.debug:
                curr += 1
                if curr > limit:
                    break

        return new_info
    

    def get_sub_comp_info(self, comp_info):
        """
        Given links to all sub-category competitions, visit these links and gather info about subcompetitions
        Input:
            comp_info: List of tuples containing info about competitions and sub-categories
        Output:
            List of tuples containing info about each comp
        """

        if self.debug:
            lim = 3
            cnt = 0

        # Hold new comp info
        lead_data = []
        speed_data = []
        boulder_data = []
        combined_data = []

        # Iterate through comps
        for comp in comp_info:
            # Preserve info about this comp
            this_comp_info = [('Competition Title', comp[0]), ('Competition Date', comp[1])]
            # Iterate through subcategories
            for subcat in comp[3:]:
                # Subcategory type
                cat_type = subcat[0][:-16]

                # Open link
                link = subcat[1]

                # Load subcategory
                self.load_page(link)

                # Lead
                if cat_type[-4:] == 'lead':
                    this_comp_info.append(('Category', cat_type[-4:]))
                    this_lead_data = self.get_data_on_page(this_comp_info)
                    lead_data.append(this_lead_data)
                # Speed
                elif cat_type[-5:] == 'speed':
                    this_comp_info.append(('Category', cat_type[-5:]))
                    this_speed_data = self.get_data_on_page(this_comp_info)
                    speed_data.append(this_speed_data)
                # Bouldering
                elif cat_type[-7:] == 'boulder' or cat_type[-10:] == 'bouldering':
                    this_comp_info.append(('Category', cat_type[-7:]))
                    this_boulder_data = self.get_data_on_page(this_comp_info)
                    boulder_data.append(this_boulder_data)
                # Combined
                elif cat_type[-8:] == 'combined':
                    this_comp_info.append(('Category', cat_type[-8:]))
                    this_combined_data = self.get_data_on_page(this_comp_info)
                    combined_data.append(this_combined_data)
                else:
                    # Find out what category this actually was so we can find edge cases
                    print(cat_type)

                if self.debug:
                    cnt += 1
                    if cnt > lim:
                        break
                
        return [lead_data, speed_data, boulder_data, combined_data]

    def make_df_from_data(self, comp_data):
        """
        Takes the scraped data available in list format and converts it to dataframes
        input:
            comp_data: List of lists of tuples specifying competition results for different categories
        output:
            List of dataframes containing data
        """
        lead_data, speed_data, boulder_data, combined_data = comp_data

        # # Build lead data df
        # lead_headers = []
        # # Find headers
        # for head in lead_data[0][0]:
        #     lead_headers.append(head[0])

        # Create lead df
        lead_df = self.build_df(lead_data)

        # Create speed df
        speed_df = self.build_df(speed_data)

        # Create boulder df
        boulder_df = self.build_df(boulder_data)

        # Create combined df
        combined_df = self.build_df(combined_data)

        return [lead_df, speed_df, boulder_df, combined_df]

    def build_df(self, cat_data):
        """
        Given the data for a category, build a df for it
        input:
            cat_data - Data scraped for a particular category
        output:
            df of the data
        """
        # Iterate through competitions, build list of dicts for df
        data_list = []
        for comp in cat_data:
            # Iterate through results per comp
            for result in comp:
                # Convert to dict
                this_dict = dict(result)
                data_list.append(this_dict)
        
        # Convert to df
        df = pd.DataFrame(data_list)

        return df


    def get_data_on_page(self, prior_info):
        """
        Helper function that scrapes the data from a complete result page and returns it in a tuple
        input:
            prior_info - Comp name, date, subcategory
        output:
            touple representing the table of results on the page
        """

        # Get table from webpage
        result_list = self.browser.find_elements_by_tag_name('tr')
        
        # Get headers
        result_headers = [x.find_elements_by_tag_name('th') for x in result_list]
        headers = [x.text for x in result_headers[0]]
        # Fix name
        headers[1] = 'LAST'
        headers.insert(2, 'FIRST')
        
        # Get table rows
        rows = [x.find_elements_by_tag_name('td') for x in result_list]
        rows = rows[1:]

        # Package data to be returned
        ret_data = []

        # Split rows into tuples and add to list
        for row in rows:
            add_this = [x for x in prior_info] + [(header, x.text) for header, x in zip(headers, row)]
            ret_data.append(add_this)

        return ret_data

    def load_page(self, link, timeout=20, wait_after=10):
        """
        Helper function that loads a page and waits for timeout
        input:
            link - Link to the page we wish to load
            timeout - Seconds to wait before timing out
            wait_after - Seconds to wait after loading
        output:
            N/A
        """

        # Visit link
        self.browser.get(link)

        # Attempt to open link
        try:
            WebDriverWait(self.browser, timeout).until(EC.visibility_of_element_located((By.XPATH,
            "//div[@class='uk-section-primary uk-section uk-section-xsmall']")))
        except TimeoutException:
            print("Timed out waiting for page " + link + " to load")
            self.browser.quit()

        # Wait for page to load
        time.sleep(wait_after)

    def check_for_new(self, comp_info):
        """
        After retrieving info about individual competitions, load previous data and compare to see
        if there are any new comps
        input:
            comp_info - tuple of info about comps scraped from the results page
        output:
            list of info in tuple form about comps that are new and should be scraped
        """

        try:
            # Load unique names of already scraped competitions
            unique_names = pd.read_csv('~/projects/ifsc-scraper/data/name_df.csv')
            # Convert to list
            unique_names = list(unique_names['Competition Title'])
        except:
            print('No comp names saved')
            unique_names = []

        # List of new competition info
        new_comp_info = []

        # Check if each comp is new
        for comp in comp_info:
            # Check if comp has been scraped or not
            if comp[0] in unique_names:
                # Don't add it to new info
                pass
            else:
                # New comp, add to be scraped
                new_comp_info.append(comp)
            
        # Return list of new comps
        return new_comp_info

    def merge_dfs(self, gathered_dfs):
        """
        Merge newly gathered dfs with old dfs
        input:
            gathered_dfs - pandas dataframes that have been gathered this run
        output:
            merged dfs
        """
        # Split into dfs
        lead_df, speed_df, boulder_df, combined_df = gathered_dfs

        # Merge each df with the exisiting data
        old_lead_df = pd.read_csv('~/projects/ifsc-scraper/data/lead_results.csv')
        old_speed_df = pd.read_csv('~/projects/ifsc-scraper/data/speed_results.csv')
        old_boulder_df = pd.read_csv('~/projects/ifsc-scraper/data/boulder_results.csv')
        old_combined_df = pd.read_csv('~/projects/ifsc-scraper/data/combined_results.csv')

        lead_df = pd.concat([lead_df, old_lead_df], ignore_index=True)
        speed_df = pd.concat([speed_df, old_speed_df], ignore_index=True)
        boulder_df = pd.concat([boulder_df, old_boulder_df], ignore_index=True)
        combined_df = pd.concat([combined_df, old_combined_df], ignore_index=True)

        return [lead_df, speed_df, boulder_df, combined_df]

    def clean_boulder(self, boulder_df):
        """
        Cleans up the columns of the boulder df
        input:
            boulder_df - pandas dataframe containing info about bouldering comps
        output:
            cleaned boulder df
        """
        # Names of the possible columns for semifinals
        semifinal_cols = ['Semi-Final', 'Semi Final', 'Semifinal', 'semi-Final', 'SemiFinal',
        'Semi final', 'Semi-final', 'Semi - Final', '1/2-Final']

        # Remove column names that aren't in this df
        for col in list(semifinal_cols):
            if col not in list(boulder_df):
                semifinal_cols.remove(col)

        # Consolidate columns
        boulder_df['New Semifinal'] = boulder_df[semifinal_cols].apply(
            lambda x: ','.join(x.dropna().astype(str)),
            axis=1
        )
        boulder_df = boulder_df.drop(semifinal_cols, axis=1)
        boulder_df = boulder_df.rename(columns={'New Semifinal':'Semifinal'})

        # Qualification 1 columns
        qual_cols = ['1. Qualification (2)', '1. Qualification', 'Qualification (Group 1)',
                 'Qualification (group A)', 'A Qualification', 'A. Qualification',
                 'Qualification A', 'Qualification Group A', 'Qualification 1']

        # Remove column names that aren't in this df
        for col in list(qual_cols):
            if col not in list(boulder_df):
                qual_cols.remove(col)

        # Consolidate columns
        boulder_df['New Qualification 1'] = boulder_df[qual_cols].apply(
            lambda x: ','.join(x.dropna().astype(str)),
            axis=1
        )
        boulder_df = boulder_df.drop(qual_cols, axis=1)
        boulder_df = boulder_df.rename(columns={'New Qualification 1':'Qualification 1'})


        # Qualification 2 columns
        qual_cols = ['2. Qualification (2)', '2. Qualification', 'Qualification (Group 2)',
                 'B Qualification', 'Qualification (group B)', 'B. Qualification',
                 'Qualification B', 'Qualification Group B', 'Qualification 2']

        # Remove column names that aren't in this df
        for col in list(qual_cols):
            if col not in list(boulder_df):
                qual_cols.remove(col)

        # Consolidate columns
        boulder_df['New Qualification 2'] = boulder_df[qual_cols].apply(
            lambda x: ','.join(x.dropna().astype(str)),
            axis=1
        )
        boulder_df = boulder_df.drop(qual_cols, axis=1)
        boulder_df = boulder_df.rename(columns={'New Qualification 2':'Qualification 2'})


        return boulder_df

    def clean_combined(self, combined_df):
        """
        Cleans up the columns of the combined df
        input:
            combined_df - pandas dataframe containing info about combined comps
        output:
            cleaned combined df
        """
        # No cleaning needed as of 10/16/2019
        return combined_df

    def clean_lead(self, lead_df):
        """
        Cleans up the columns of the lead df
        input:
            lead_df - pandas dataframe containing info about lead comps
        output:
            cleaned lead df
        """

        # Names of the possible columns for semifinals
        semifinal_cols = ['1/2 Final', 'Semi-Final', 'Semi Final', 'SemiFinal', 'Semi-final', '1/2 - Final', '1/2-Final', 'Semi - Final', 'Semifinal']

        # Remove column names that aren't in this df
        for col in list(semifinal_cols):
            if col not in list(lead_df):
                semifinal_cols.remove(col)
        
        # Consolidate columns
        lead_df['New Semifinal'] = lead_df[semifinal_cols].apply(
            lambda x: ','.join(x.dropna().astype(str)),
            axis=1
        )
        lead_df = lead_df.drop(semifinal_cols, axis=1)
        lead_df = lead_df.rename(columns={'New Semifinal':'Semifinal'})

        # Names of the possible columns for qualification 1
        qual_cols = ['1. Qualification 1', '1. Qualification',
        'Qualification 1', '1. Qualification:', '1.Qualification',
        'Group A Qualification', '1 Qualification', 'Qualification 1']
        
        # Remove column names that aren't in this df
        for col in list(qual_cols):
            if col not in list(lead_df):
                qual_cols.remove(col)

        # Consolidate columns
        lead_df['New Qualification'] = lead_df[qual_cols].apply(
            lambda x: ','.join(x.dropna().astype(str)),
            axis=1
        )
        lead_df = lead_df.drop(qual_cols, axis=1)
        lead_df = lead_df.rename(columns={'New Qualification':'Qualification 1'})
        
        # Names of the possible columns for qualification 2
        qual_cols = ['2. Qualification', '2. Qualification 2', 'Qualification 2', 'Group B Qualification', 'Qualification 2']

        # Remove column names that aren't in this df
        for col in list(qual_cols):
            if col not in list(lead_df):
                qual_cols.remove(col)

        lead_df['New Qualification'] = lead_df[qual_cols].apply(
            lambda x: ','.join(x.dropna().astype(str)),
            axis=1
        )
        lead_df = lead_df.drop(qual_cols, axis=1)
        lead_df = lead_df.rename(columns={'New Qualification':'Qualification 2'})

        # Drop this random nan column is it's there
        try:
            lead_df = lead_df.drop(['Unnamed: 18'], axis=1)
        except:
            pass

        return lead_df

    def clean_speed(self, speed_df):
        """
        Cleans up the columns of the speed df
        input:
            speed_df - pandas dataframe containing info about speed comps
        output:
            cleaned speed df
        """

        # Names of the possible columns for 1/8 finals
        eighths = ['1/8 - Final', '1_8 - Final']

        # Remove column names that aren't in this df
        for col in list(eighths):
            if col not in list(speed_df):
                eighths.remove(col)

        speed_df['New Eighths'] = speed_df[eighths].apply(
            lambda x: ','.join(x.dropna().astype(str)),
            axis=1
        )
        speed_df = speed_df.drop(eighths, axis=1)
        speed_df = speed_df.rename(columns={'New Eighths':'1/8 - Final'})

        return speed_df

    def scrape(self):
        """
        Scrape the website, build dataframes, save dataframes
        input:
            N/A
        output:
            N/A
        """
        lead_df, speed_df, boulder_df, combined_df = self.make_df_from_data(self.get_sub_comp_info(self.get_complete_result_links(self.check_for_new(self.get_comp_links()))))

        # Merge new data with old data
        lead_df, speed_df, boulder_df, combined_df = self.merge_dfs([lead_df, speed_df, boulder_df, combined_df])

        # Clean data before saving
        lead_df = self.clean_lead(lead_df)
        speed_df = self.clean_speed(speed_df)
        boulder_df = self.clean_boulder(boulder_df)
        combined_df = self.clean_combined(combined_df)

        lead_df.to_csv('lead_results.csv', index=False)
        speed_df.to_csv('speed_results.csv', index=False)
        boulder_df.to_csv('boulder_results.csv', index=False)
        combined_df.to_csv('combined_results.csv', index=False)


def main():
    # Create scraper object
    scraper = IFSCScraper()

    # Run scraper
    scraper.scrape()

if __name__ == '__main__':
    main()