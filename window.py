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

import firebase_admin
from firebase_admin import credentials
from firebase_admin import firestore

import csv

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
                    self.scrape_song_info(selector.format(i, i, i), i)
                except IndexError as e:
                    print(e)
                    if len(self.browser.window_handles) > 1:
                        # Close the tab or window
                        self.browser.close()
                        # Switch back to the old tab or window
                        self.browser.switch_to.window(self.browser.window_handles[0])
                except WebDriverException as e:
                    print("ERROR: WebDriverException", e)
                except:
                    print("UNKNOWN ERROR")

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
                return

            song_name = soundcloud_elems[1].text.strip()
            song_listens = 0

            if len(soundcloud_elems) == 3:
                song_listens = self.format_soundcloud_listens(soundcloud_elems[2].text.strip())

            ig_handle = self.scrape_instagram_handle(soundcloud_elems[0])

            if ig_handle != 'TIMEOUT ERROR':
                self.db.add_artist(soundcloud_name, song_name, song_listens, self.playlist_genre, ig_handle)
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

    def format_soundcloud_listens(self, str):
        if "K" not in str and "M" not in str:
            return int(str.replace(',', ''))
        if "K" in str:
            return float(str[:-1]) * 1000
        elif "M" in str:
            return float(str[:-1]) * 1000 * 1000

class MyDb:
    def __init__(self):
        # Use the application default credentials
        cred = credentials.Certificate("./soundcloud-scraper-firebase-adminsdk-tsxsi-82b9347dd3.json")
        firebase_admin.initialize_app(cred)

        self.db_coll = firestore.client().collection(u'artists')
        self.all_documents = self.db_coll.stream()
        self.artist_set = set(map(lambda doc: doc.id,self.all_documents))


    def add_artist(self, soundcloud_name, song_name, song_listens, genre, ig_handle):
        try:
            self.db_coll.document(soundcloud_name).set({
                u'soundcloud_name': soundcloud_name,
                u'song_name': song_name,
                u'song_listens': song_listens,
                u'genre': genre,
                u'timestamp': firestore.SERVER_TIMESTAMP,
                u'ig_handle': ig_handle,
            })
        except ValueError as e:
            print("ERROR: Value Error, couldn't add {} to db".format(soundcloud_name), e)
        except:
            print("ERROR: 503 Database unavailable.")
            time.sleep(5)
    def get_db_as_csv(self):
        fields = [ 'soundcloud_name', 'song_name', 'genre', 'song_listens',  'timestamp', 'ig_handle' ]

        with open('artist_db.csv', 'w') as csvfile:
            # creating a csv writer object
            csvwriter = csv.DictWriter(csvfile, fieldnames=fields)
            # writing the fields
            csvwriter.writeheader()
            # writing the data rows
            for doc in self.db_coll.stream():
                try:
                    csvwriter.writerow(doc.to_dict())
                except UnicodeEncodeError:
                    doc_copy = doc.to_dict()
                    csvwriter.writerow({
                        u'timestamp': doc_copy.get("timestamp"),
                        u'song_name': doc_copy.get("song_name").encode('utf-8').strip(),
                        u'ig_handle': doc_copy.get("ig_handle").encode('utf-8').strip(),
                        u'song_listens': doc_copy.get("song_listens"),
                        u'genre': doc_copy.get("genre").encode('utf-8').strip(),
                        u'soundcloud_name': doc_copy.get("soundcloud_name").encode('utf-8').strip()
                    })
    def has_artist(self, soundcloud_name):
        return soundcloud_name in self.artist_set



window = Tk()
mywin = MyWindow(window)
window.title('Soundcloud Webscraper')
window.geometry("400x300+10+10")
window.mainloop()
