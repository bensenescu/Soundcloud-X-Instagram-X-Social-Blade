import time

from tkinter import *
from tkinter import filedialog

from datetime import datetime

from selenium import webdriver
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException
from selenium.common.exceptions import StaleElementReferenceException
from selenium.common.exceptions import WebDriverException
from selenium.common.exceptions import InvalidSessionIdException

import requests
import xml.etree.ElementTree as ET
from bs4 import BeautifulSoup

import classes.mydb as MyDb

def mergeDict(d1, d2):
  merged = d1.copy()
  merged.update(d2)
  return merged

class MyWindow:
    def __init__(self, win):
        self.win = win
        self.lbl1 = Label(win, text='Soundcloud Playlist:')
        self.t1 = Entry(bd=3)
        self.lbl1.place(x=60, y=50)
        self.t1.place(x=200, y=50)

        self.lbl4 = Label(win, text='Which song should it start on?')
        self.t4 = Entry(bd=3)
        self.lbl4.place(x=30, y=100)
        self.t4.place(x=200, y=100)

        self.lbl2 = Label(win, text='How many songs are in the playlist?')
        self.t2 = Entry(bd=3)
        self.lbl2.place(x=30, y=150)
        self.t2.place(x=200, y=150)

        self.lbl3 = Label(win, text='What genre is this playlist?')
        self.t3 = Entry(bd=3)
        self.lbl3.place(x=30, y=200)
        self.t3.place(x=200, y=200)

        self.b1 = Button(win, text='Start', command=self.start_scraping)
        self.b1.place(x=100, y=250)
        # window.filename = filedialog.askopenfilename(initialdir="/", title="Select file",
        #                                              filetypes=(("jpeg files", "*.jpg"), ("all files", "*.*")))

    def start_scraping(self):
        url = str(self.t1.get()).strip()
        start_song = int(self.t4.get())
        len = int(self.t2.get())
        genre = str(self.t3.get()).strip()
        scraper = MyScraper(url, start_song, len, genre)
        scraper.scrape_all_songs()
        exit()

class MyScraper:
    def __init__(self, soundcloud_url, start_song, playlist_len, playlist_genre):
        self.browser = webdriver.Safari()
        self.browser.maximize_window()
        self.original_window = self.browser.current_window_handle

        self.start_song = start_song
        self.soundcloud_url = soundcloud_url
        self.playlist_len = playlist_len
        self.playlist_genre = playlist_genre
        self.browser.get(self.soundcloud_url)
        self.db = MyDb()

    def scrape_all_songs(self):
        for i in range(self.start_song, self.playlist_len + 1):
            try:
                self.browser.get(self.soundcloud_url)
                selector = '.sc-border-light-bottom:nth-child({}) .sc-ministats-plays , .sc-border-light-bottom:nth-child({}) .sc-font-light , .sc-border-light-bottom:nth-child({}) .sc-link-light'

                try:
                    song_info_dict = self.scrape_song_info(selector.format(i, i, i), i)
                    if song_info_dict != 'ALREADY ADDED':
                        metric_dict = self.scrape_metric_info(song_info_dict.get("ig_handle"))
                        combined_dict = mergeDict(song_info_dict, metric_dict)
                        self.db.add_artist(combined_dict)
                    
                except IndexError as e:
                    print(e)
                    if len(self.browser.window_handles) > 1:
                        # Close the tab or window
                        self.browser.close()
                        # Switch back to the old tab or window
                        self.browser.switch_to.window(self.browser.window_handles[0])
                except WebDriverException as e:
                    print("ERROR: WebDriverException", e)
                # except:
                #     print("UNKNOWN ERROR")

                if i % 10 == 0:
                    print("{} / {}".format(i, self.playlist_len))

            except InvalidSessionIdException as e:
                self.browser = webdriver.Safari()
                self.browser.maximize_window()
                print("ERROR: Invalid Sesssion.", e)

        self.db.get_db_as_csv()
        self.browser.quit()

    def scrape_song_info(self, selector, index):
        try:
            elem = WebDriverWait(self.browser, 1).until(EC.element_to_be_clickable((By.TAG_NAME, "body")))
            # self.browser.find_element_by_tag_name("body")
            no_of_page_downs = round(float(index) / 10) + 1

            while no_of_page_downs:
                elem.send_keys(Keys.PAGE_DOWN)
                time.sleep(0.2)
                no_of_page_downs -= 1

            time.sleep(1)
            # soundcloud_elems = WebDriverWait(self.browser, 1).until(EC.presence_of_all_elements_located((By.CSS_SELECTOR, selector)))
            soundcloud_elems = self.browser.find_elements_by_css_selector(selector)

            soundcloud_name = soundcloud_elems[0].text.strip()

            if self.db.has_artist(soundcloud_name):
                return 'ALREADY ADDED'

            song_name = soundcloud_elems[1].text.strip()
            song_listens = 0

            if len(soundcloud_elems) == 3:
                song_listens = self.format_soundcloud_listens(soundcloud_elems[2].text.strip())

            ig_handle = self.scrape_instagram_handle(soundcloud_elems[0])

            return {
                u'soundcloud_name': soundcloud_name,
                u'song_name': song_name,
                u'song_listens': song_listens,
                u'genre': self.playlist_genre,
                u'timestamp': firestore.SERVER_TIMESTAMP,
                u'ig_handle': ig_handle
            }

        except StaleElementReferenceException as e:
            print("ERROR: scrape_song_info", e)

    def scrape_instagram_handle(self, profile_elem):
        profile_elem.send_keys(Keys.RETURN)

        time.sleep(1)
        if len(self.browser.find_elements_by_css_selector(".sc-social-logo-instagram")) > 0:
            self.browser.find_element_by_css_selector(".sc-social-logo-instagram").click()
            time.sleep(.5)

            self.browser.switch_to.window(self.browser.window_handles[1])
            try:
                handle = WebDriverWait(self.browser, 5).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, ".fDxYl"))).text.strip()
            except TimeoutException as e:
                if len(self.browser.window_handles) > 1:
                    # Close the tab or window
                    self.browser.close()
                    # Switch back to the old tab or window
                    self.browser.switch_to.window(self.browser.window_handles[0])
                print('ERROR: scrape_instagram_handle', e)
                return 'TIMEOUT ERROR'

            # playlistDataFormatted[i]["igHandle"] = browser.find_element_by_css_selector(".fDxYl").text.strip()
            # Close the tab or window
            if len(self.browser.window_handles) > 1:
                # Close the tab or window
                self.browser.close()
                # Switch back to the old tab or window
                self.browser.switch_to.window(self.browser.window_handles[0])
            return handle

        return ''
    
    def scrape_metric_info(self, ig_handle):
        # url of rss feed
        url = 'https://socialblade.com/instagram/user/{}'.format(ig_handle)

        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 6.1) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/41.0.2228.0 Safari/537.3'
        }
        # creating HTTP response object from given url
        resp = requests.get(url, headers=headers)

        if resp.status_code == 200:
            with open('filename.xml', 'wb') as f:
                f.write(resp.content)
        
        try:
            with open("filename.xml") as fp:
                soup = BeautifulSoup(fp, "html.parser")
                spans = soup.find_all("div", {"class": "YouTubeUserTopInfo"})
                metrics = []
                for i in range(0, len(spans) - 1):
                    metrics.append(spans[i].find(
                        "span", {"style": "font-weight: bold;"}).text.strip())

                return {
                    u'media_uploads': metrics[0],
                    u'followers': metrics[1],
                    u'following': metrics[2],
                    u'engagement_rate': metrics[3],
                    u'avg_likes': metrics[4],
                    u'avg_comments': metrics[5],
                }
            
        except IndexError as e:
            print("ERROR: IndexError")
            return {
                u'media_uploads': '',
                u'followers': '',
                u'following': '',
                u'engagement_rate': '',
                u'avg_likes': '',
                u'avg_comments': '',
            }

    def format_soundcloud_listens(self, str):
        if "K" not in str and "M" not in str:
            return int(str.replace(',', ''))
        if "K" in str:
            return float(str[:-1]) * 1000
        elif "M" in str:
            return float(str[:-1]) * 1000 * 1000

window = Tk()
mywin = MyWindow(window)
window.title('Soundcloud Webscraper')
window.geometry("400x300+10+10")
window.mainloop()
