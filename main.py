import bs4 # library for pulling data from html
import requests # library for http interfacing
import csv # library for writing/reading from csv's
from tqdm import tqdm # library for progress bars
import re # library for regex search

#import sys
#reload(sys)
#sys.setdefaultencoding('utf8')

RGL_WEBSITE = "http://rgl.faa.gov"
FAR_PART = 25

# FAR_reg is a dictionary with part number, section number, amendment, date and text

def main():

    # pull in CFR14 historical regulations page as bs4 page
    r  = requests.get(RGL_WEBSITE + "/Regulatory_and_Guidance_Library/rgFAR.nsf/HistoryFARPartSection!OpenView")
    data = r.text
    soup = bs4.BeautifulSoup(data, features="html.parser")

    # identify URL link to relevant FAR part
    part_link = find_links(soup, "Show details for Part " + " "* (3-len(str(FAR_PART))) +  str(FAR_PART), True, False, False)

    r = requests.get(RGL_WEBSITE + str(part_link[0]['link']))
    part_data = r.text
    part_soup = bs4.BeautifulSoup(part_data, features="html.parser")

    section_links = find_section(part_soup)
    # for every section
    #find_link("Show Details for Section ")

    # for every revision

    # extract amendment, date, text

    # add to csv

# finds a url in the html source of a webpage based on finding a keyphrase and extracting the href associated with it
def find_links(text, keyphrase, check_part, check_sec, check_amdt):

    link_prefix = "href="
    
    links = [] # stores URL links
    regex_pattern = re.compile(r'\d\d/\d\d/\d\d\d\d')

    for line in text:
        # find line with key phrase in it
        if check_amdt:
            regex_keyphrase = regex_pattern.search(str(line))
            if regex_keyphrase:
                idx_keyphrase_start = regex_keyphrase.start()
            else:
                idx_keyphrase_start = 0
        else:
            idx_keyphrase_start = str(line).find(keyphrase)

        if idx_keyphrase_start > 0:
            # extract index of line where prefix ends (if not present = -1)
            if check_sec:
                idx_keyphrase_start += len(keyphrase)
                idx_keyphrase_end = str(line)[idx_keyphrase_start:].find('\"')
                section_number = str(line)[idx_keyphrase_start:idx_keyphrase_start+idx_keyphrase_end]
            else:
                section_number = FAR_PART
                
            idx = str(line).find(link_prefix)
           
            if idx > 0:
                start_idx = idx + len(link_prefix) + 1 # add 1 to move past quotation mark
                reduced_line = str(line)[start_idx:]
                end_idx = reduced_line.find('\"') + start_idx # stop at the next quotation mark
                
                if end_idx > start_idx:
                    # extract sub string between index of prefix ending and next quotation mark
                    reduced_link = str(line)[start_idx:end_idx]
                    # add link to list of links
                    dict_link = {"link": clean_link(reduced_link), "number": section_number}
                    links.append(dict_link)   
                else:
                    raise Exception("ERROR - no valid END index found")
                
            else:
                raise Exception("ERROR - no START index found")
            
    if len(links) < 1:
        print("For phrase: " +  keyphrase)
        raise Exception("ERROR - no links found")
    elif check_part and len(links) > 1:
        raise Exception("ERROR - more than one link found for FAR part")
           
    # return every link that matches the prefix
    return links

# extracts link for all section for a given FAR part
def find_section(soup):

    # returns a list of all links for that part
    part_links = find_links(soup, "Show details for Sec. ", False, True, False)
    data_list = []
    
    print("Extracting sections for FAR part: " + str(FAR_PART))
    
    # for every section
    for section_link in tqdm(part_links):
        # get soup of each section
        r = requests.get(RGL_WEBSITE + str(section_link['link']))
        data = r.text
        soup = bs4.BeautifulSoup(data, features="html.parser")
        # extract amdt links of each section
        amdt_links = find_links(soup, "Hide details for Sec. ", False, False, True)

        # for every amdt
        for amdt_link in amdt_links:
            # add the admendment to the list
            data_list.append(extract_amdt_data(amdt_link))
            
    csv_file = write_section_data_CSV(data_list)
        
    return csv_file

# extracts the html between two different section links
#def extract_html_section(soup, section_1, section_2):

# cleans up the string for a link
def clean_link(link):

    link_remove_amp = link.replace("&amp;", "&") # fix character for & representation
    link_increase_count = link_remove_amp.replace("Count=200", "Count=2000") # extend to cover all sections

    return link_increase_count
        
# given the html of the page for the specific amendment section extract and return relevant data in a dictionary
def extract_amdt_data(link):
    
    r = requests.get(RGL_WEBSITE + str(link['link']))
    data = r.text
    soup = bs4.BeautifulSoup(data, features="html.parser")
    text_soup = soup.find("div", {"id": "xSec1"})

    title_empty = True

    amdt_data = {"section": "", "title": "", "text": "", "amdt": "", "amdt_date": ""}
    
    for line in text_soup.contents:
        line_string = str(line)
        if line_string[0] != '<' and len(line_string) > 1:
            if line_string[1:5] == "Sec.":
                amdt_data["section"] = line_string.split('.')[-1]
            elif line_string[1:6] == "Amdt.":
                line_string.replace(';', ',')
                line_string = line_string.split(',')
                amdt_data["amdt"] = line_string[0].split('-')[-1]
                amdt_data["amdt_date"] = line_string[1].split('.')[-1].strip()
            elif title_empty:
                amdt_data["title"] = line_string[1:]
                title_empty = False
            else:
                 amdt_data["text"] = amdt_data["text"] + line_string

    print(amdt_data["section"])
    return amdt_data

# given relevant data in a dictionary add it to a CSV
def write_section_data_CSV(amdt_data):

    keys = amdt_data[0].keys()
    title_data = {"section": "FAR Section "+str(FAR_PART) , "title": "Section Title", "text": "Section Text", "amdt": "Amdt. #", "amdt_date": "Amdt. Date"}
    
    # FAR section (2X.XXX) | Amdt | Date | Text

    with open("FAR Part " + str(FAR_PART), 'w') as csv_file:
        writer = csv.DictWriter(csv_file, keys)
        writer.writerow(title_data)
        writer.writerows(amdt_data)
        
    return csv_file
        
main()
