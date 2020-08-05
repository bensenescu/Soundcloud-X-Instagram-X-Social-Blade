import os
import sys
import time
import csv
from datetime import datetime

from selenium import webdriver
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import NoSuchElementException
from selenium.common.exceptions import SessionNotCreatedException
from selenium.common.exceptions import TimeoutException
from selenium.common.exceptions import StaleElementReferenceException


def check_args():
    if len(sys.argv) != 4 or sys.argv[1] == "--help":
        print("-----------------Manual-----------------\n"
              + "First Argument: Valid Soundcloud Playlist\n"
              + "Second Argument: Csv to Edit: ex. artist.csv\n"
              + "Third Argument: Is this a new File? Write w if so, a to append.\n")
        sys.exit()

def format_soundcloud_listens(str):
    if "K" not in str and "M" not in str:
        return str
    if "K" in str:
        return float(str[:-1]) * 1000
    elif "M" in str:
        return float(str[:-1]) * 1000 * 1000

def get_playlist_songs(browser, playlistUrl, page_downs):
    browser.get(playlistUrl)
    time.sleep(1)

    elem = browser.find_element_by_tag_name("body")

    no_of_pagedowns = page_downs

    while no_of_pagedowns:
        elem.send_keys(Keys.PAGE_DOWN)
        time.sleep(0.2)
        no_of_pagedowns -= 1

    elems = browser.find_elements_by_css_selector(
        '.m-disabled .trackItem__additional , .trackItem__blockMsg , .sc-ministats-plays , .sc-font-light , .trackItem__username,.sc - ministats - plays,.sc - link - dark.sc - font - light')
    ''
    playlistDataFormatted = []

    i = 0
    while i < len(elems) - 2:
        playlistDataFormatted.append({
            'artist': elems[i].text.strip(),
            'song': elems[i + 1].text.strip(),
            'numberOfListens': format_soundcloud_listens(elems[i + 2].text.strip()),
            'date': datetime.today().strftime('%Y-%m-%d'),
            'igHandle': 'n/a'})

        if elems[i + 2].text.strip() == "Not available in United States":
            i += 1

        i += 3

    return playlistDataFormatted

def write_dict_csv(fields, dict):
    with open(sys.argv[2], 'w') as csvfile:
        # creating a csv writer object
        csvwriter = csv.DictWriter(csvfile, fieldnames=fields)
        # writing the fields
        csvwriter.writeheader()
        # writing the data rows
        for row in dict:
            try:
                csvwriter.writerow(row)
            except UnicodeEncodeError:
                print("ERROR: Could not write artist due to emoji", row.get("artist"))

def append_dict_csv(fields, dict):
    with open(sys.argv[2], 'a') as csvfile:
        # creating a csv writer object
        csvwriter = csv.DictWriter(csvfile, fieldnames=fields)
        # writing the data rows
        for row in dict:
            try:
                csvwriter.writerow(row)
            except UnicodeEncodeError:
                print("ERROR: Could not write artist due to emoji", row.get("artist"))

def reset_browser(browser, playlistUrl):
    print(browser.window_handles, browser.current_url)
    if len(browser.window_handles) > 1:
        browser.close()
        browser.switch_to.window(browser.window_handles[0])

    browser.get(playlistUrl)

def switch_window_add_handle(browser, playlistDataDict, i, playlistUrl):
    try:
        window_original = browser.window_handles[0]
        window_after = browser.window_handles[1]
        browser.switch_to.window(window_after)
        try:
            playlistDataDict[i]["igHandle"] = WebDriverWait(browser, 3).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, ".fDxYl"))).text.strip()

        except NoSuchElementException:
            print("Error: Instagram data retrieval failed for %s." % playlistDataDict[i].get("artist"))
            reset_browser(browser, playlistUrl)

        except TimeoutException:
            try:
                switch_window_add_handle(browser, playlistDataDict, i, playlistUrl)
            except TimeoutException:
                print("Error: Took too long to get IG for %s." % playlistDataDict[i].get("artist"))
                reset_browser(browser, playlistUrl)


        # playlistDataFormatted[i]["igHandle"] = browser.find_element_by_css_selector(".fDxYl").text.strip()
        # Close the tab or window
        browser.close()
        # Switch back to the old tab or window
        browser.switch_to.window(window_original)

    except IndexError:
        print("ERROR: No IG Window Opened for %s" % playlistDataDict[i].get("artist"))
        reset_browser(browser, playlistUrl)


# def manage_progress(progress_breaks, i):
#     for bp in reversed(progress_breaks):
#         if i == bp:
#             try:
#                 print("{0}% complete scraping your playlist!".format(round(bp / progress_breaks[len(progress_breaks) - 1])))
#                 break
#             except ZeroDivisionError:
#                 break

def scroll_body(browser, artistName, i, playlistUrl):
    try:
        print('test', artistName, browser.current_url)
        elem = WebDriverWait(browser, 2).until(
            EC.element_to_be_clickable((By.TAG_NAME, "body")))
        no_of_pagedowns = i % 10

        while no_of_pagedowns:
            elem.send_keys(Keys.PAGE_DOWN)
            time.sleep(0.2)
            no_of_pagedowns -= 1

    except StaleElementReferenceException:
        print("Error: Stale Element Exception for %s at url %s." % (artistName, browser.current_url))
        reset_browser(browser, playlistUrl)

def get_ig_handles(browser, playlistDataDict, playlistUrl):
    for i in range(len(playlistDataDict)):
        # manage_progress(progress_breaks, i)

        scroll_body(browser, playlistDataDict[i].get("artist"), i, playlistUrl)

        try:
            selector = ".sc-border-light-bottom:nth-child(%s) .sc-link-light" % str(i + 1)
            WebDriverWait(browser, 2).until(
                EC.element_to_be_clickable((By.CSS_SELECTOR, selector))).send_keys(Keys.RETURN)

            try:
                WebDriverWait(browser, 1).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, ".sc-social-logo-instagram"))).click()
                switch_window_add_handle(browser, playlistDataDict, i, playlistUrl)
            except TimeoutException:
                print('No Instagram')
                reset_browser(browser, playlistUrl)

        except TimeoutException:
            print("list not loaded")
            reset_browser(browser, playlistUrl)

        reset_browser(browser, playlistUrl)

    return playlistDataDict

def main():
    check_args()
    playlistUrl = sys.argv[1]

    browser = webdriver.Safari()
    print('Successfully started scraping your playlist!!')
    browser.maximize_window()

    playlistDataDict = get_playlist_songs(browser, playlistUrl, page_downs=10)
    print(playlistDataDict)

    # progress_breaks = [x * round((float(len(playlistDataDict)) / 10) * 100) for x in range(10)]
    # # if len(playlistDataDict) < 10:
    # #     progress_breaks = []

    print(len(playlistDataDict))
    playlistDataWithIG = get_ig_handles(browser, playlistDataDict, playlistUrl)

    fields = ['artist', 'song', 'numberOfListens', 'date', 'igHandle']
    if (sys.argv[3] == "w"):
        write_dict_csv(fields, playlistDataWithIG)

    elif (sys.argv[3] == "a"):
        append_dict_csv(fields, playlistDataWithIG)

    browser.quit()

try:
    main()
except SessionNotCreatedException:
    print('ERROR: Session Not Created Exception, The Safari instance is already paired with another WebDriver session.')
    os.system('pkill safaridriver')
    print('Please make sure to close any windows with safari open!')
