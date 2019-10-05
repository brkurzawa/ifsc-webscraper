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
            
            # Visit link
            self.browser.get(comp_link)

            # Wait 20 seconds for loading
            timeout = 20

            # Open link, return html
            try:
                WebDriverWait(self.browser, timeout).until(EC.visibility_of_element_located((By.XPATH,
                "//div[@class='uk-section-primary uk-section uk-section-xsmall']")))
            except TimeoutException:
                print("Timed out waiting for page " + comp_link + " to load")
                self.browser.quit()

            # Wait to be safe
            time.sleep(3)

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
                elif cat_type[-7:] == 'boulder':
                    this_comp_info.append(('Category', cat_type[-7:]))
                    this_boulder_data = self.get_data_on_page(this_comp_info)
                    boulder_data.append(this_boulder_data)
                # Combined
                elif cat_type[-8:] == 'combined':
                    this_comp_info.append(('Category', cat_type[-8:]))
                    this_combined_data = self.get_data_on_page(this_comp_info)
                    combined_data.append(this_combined_data)

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
        headers[1] = 'FIRST'
        headers.insert(2, 'LAST')
        
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

    def scrape(self):
        """
        Scrape the website, build dataframes, save dataframes
        input:
            N/A
        output:
            N/A
        """
        lead_df, speed_df, boulder_df, combined_df = self.make_df_from_data(self.get_sub_comp_info(self.get_complete_result_links(self.get_comp_links())))

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