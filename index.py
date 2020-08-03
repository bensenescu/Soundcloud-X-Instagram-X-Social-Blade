import sys
import time
import csv 
from datetime import datetime

from selenium import webdriver
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

if len(sys.argv) != 4 or sys.argv[1] == "--help":
  print("-----------------Manual-----------------\n"
    + "First Argument: Valid Soundcloud Playlist\n"
    + "Second Argument: Csv to Edit: ex. artist.csv\n"
    + "Third Argument: Is this a new File? Write w if so, a to append.\n")
  sys.exit()

def formatSoundcloudListens(str):
  if "K" not in str and "M" not in str:
    return str
  if "K" in str:
    return float(str[:-1]) * 1000
  elif "M" in str:
    return float(str[:-1]) * 1000 * 1000
  
playlistUrl = sys.argv[1]

browser = webdriver.Safari()
browser.maximize_window()

browser.get(playlistUrl)
time.sleep(1)

elem = browser.find_element_by_tag_name("body")

no_of_pagedowns = 10

while no_of_pagedowns:
    elem.send_keys(Keys.PAGE_DOWN)
    time.sleep(0.2)
    no_of_pagedowns-=1

elems = browser.find_elements_by_css_selector('.sc-ministats-plays , .sc-link-dark.sc-font-light , .trackItem__username')

playlistDataFormatted = []

i = 0
while i < len(elems) - 2:
  playlistDataFormatted.append({
    'artist': elems[i].text.strip(), 
    'song': elems[i+1].text.strip(), 
    'numberOfListens': formatSoundcloudListens(elems[i+2].text.strip()), 
    'date': datetime.today().strftime('%Y-%m-%d'), 
    'igHandle': 'n/a'})
  i+=3

for i in range(len(playlistDataFormatted)):
  try:
    elem = browser.find_element_by_tag_name("body")
    no_of_pagedowns = 10

    while no_of_pagedowns:
      elem.send_keys(Keys.PAGE_DOWN)
      time.sleep(0.2)
      no_of_pagedowns-=1  
  
    selector = ".sc-border-light-bottom:nth-child(%s) .sc-link-light" % str(i + 1)
    browser.find_element_by_css_selector(selector).send_keys(Keys.RETURN)
    time.sleep(1)

    if len(browser.find_elements_by_css_selector(".sc-social-logo-instagram")) > 0:
      browser.find_element_by_css_selector(".sc-social-logo-instagram").click()
      time.sleep(1)
      window_original = browser.window_handles[0]
      window_after = browser.window_handles[1]
      browser.switch_to.window(window_after)
      time.sleep(1)
      playlistDataFormatted[i]["igHandle"] = WebDriverWait(browser, 20).until(EC.presence_of_element_located((By.CSS_SELECTOR, ".fDxYl"))).text.strip()
      # playlistDataFormatted[i]["igHandle"] = browser.find_element_by_css_selector(".fDxYl").text.strip()
      #Close the tab or window
      browser.close()
      #Switch back to the old tab or window
      browser.switch_to.window(window_original)

    browser.get(playlistUrl)
    time.sleep(1)
  except: 
    if len(browser.window_handles) > 1:
      browser.close() 
      browser.switch_to.window(browser.window_handles[0])
    print("Error: Instagram data retrieval failed for %s." % playlistDataFormatted[i].get("artist"))
    browser.get(playlistUrl)

fields = ['artist', 'song', 'numberOfListens', 'date', 'igHandle'] 

if (sys.argv[3] == "w"):
  with open(sys.argv[2], 'w') as csvfile:
    # creating a csv writer object  
    csvwriter = csv.DictWriter(csvfile, fieldnames = fields )
    # writing the fields  
    csvwriter.writeheader()
    # writing the data rows  
    for row in playlistDataFormatted:
      try:
        csvwriter.writerow(row) 
      except: 
        print("ERROR: Could not write row.", row)
elif (sys.argv[3] == "a"):
  with open(sys.argv[2], 'a') as csvfile:
    # creating a csv writer object  
    csvwriter = csv.DictWriter(csvfile, fieldnames = fields )
    # writing the data rows  
    for row in playlistDataFormatted:
      try:
        csvwriter.writerow(row) 
      except: 
        print("ERROR: Could not write row.", row)

browser.quit()
