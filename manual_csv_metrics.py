import requests
from bs4 import BeautifulSoup
import firebase_admin
from firebase_admin import credentials
from firebase_admin import firestore
import time

import csv

class MyDb:
    def __init__(self):
        # Use the application default credentials
        cred = credentials.Certificate("./soundcloud-scraper-firebase-adminsdk-tsxsi-82b9347dd3.json")
        firebase_admin.initialize_app(cred)

        self.db_coll = firestore.client().collection(u'artists')
        self.all_documents = self.db_coll.stream()
        self.artist_set = set(map(lambda doc: doc.id,self.all_documents))

    def add_artist(self, artist_dict):
        try:
            self.db_coll.document(artist_dict.get("soundcloud_name")).set({
                u'soundcloud_name': artist_dict.get("soundcloud_name"),
                u'song_name': artist_dict.get("song_name"),
                u'song_listens': artist_dict.get("song_listens"),
                u'genre': artist_dict.get("genre"),
                u'timestamp': artist_dict.get("timestamp"),
                u'ig_handle': artist_dict.get("ig_handle"),
                u'media_uploads': artist_dict.get("media_uploads"),
                u'followers': artist_dict.get("followers"),
                u'following': artist_dict.get("following"),
                u'engagement_rate': artist_dict.get("engagement_rate"),
                u'avg_likes': artist_dict.get("avg_likes"),
                u'avg_comments': artist_dict.get("avg_comments")
            })
        except ValueError as e:
            print("ERROR: Value Error, couldn't add {} to db".format(
                artist_dict.get("soundcloud_name")), e)
        # except:
        #     print("ERROR: 503 Database unavailable.")
        #     time.sleep(5)

    def get_db_as_csv(self):
        fields = ['soundcloud_name', 'song_name', 'genre',
                  'song_listens', 'timestamp', 'ig_handle',
                  'media_uploads', 'followers', 'following',
                  'engagement_rate', 'avg_likes', 'avg_comments']

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
                        u'soundcloud_name': doc_copy.get("soundcloud_name").encode('utf-8').strip(),
                        u'media_uploads': doc_copy.get("media_uploads"),
                        u'followers': doc_copy.get("followers"),
                        u'following': doc_copy.get("following"),
                        u'engagement_rate': doc_copy.get("engagement_rate"),
                        u'avg_likes': doc_copy.get("avg_likes"),
                        u'avg_comments': doc_copy.get("avg_comments"),
                    })

    def has_artist(self, soundcloud_name):
        return soundcloud_name in self.artist_set


def load_xml(ig_handle):
    time.sleep(1)
    # url of rss feed
    url = 'https://socialblade.com/instagram/user/{}'.format(ig_handle)

    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 6.1) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/41.0.2228.0 Safari/537.3'
    }
    # creating HTTP response object from given url
    resp = requests.get(url, headers=headers)
    print('resp', resp.status_code)

    if resp.status_code == 200:
        with open('filename.xml', 'wb') as f:
            print('new content')
            f.write(resp.content)

def get_metrics_from_xml():
    with open("filename.xml") as fp:
        soup = BeautifulSoup(fp, "html.parser")
        spans = soup.find_all("div", {"class": "YouTubeUserTopInfo"})
        print(spans)
        metrics = []
        for i in range(0, len(spans) - 1):
            metrics.append(spans[i].find(
                "span", {"style": "font-weight: bold;"}).text.strip())
        
        print('metrics', metrics)
        return {
            u'media_uploads': metrics[0],
            u'followers': metrics[1],
            u'following': metrics[2],
            u'engagement_rate': metrics[3],
            u'avg_likes': metrics[4],
            u'avg_comments': metrics[5],
        }
#   except IndexError as e:
#     print("ERROR: IndexError")
#     return {
#             u'media_uploads': '',
#             u'followers': '',
#             u'following': '',
#             u'engagement_rate': '',
#             u'avg_likes': '',
#             u'avg_comments': '',
#         }

def is_manually_added_ig(artist_dict):
    return artist_dict.get("ig_handle") != "" and artist_dict.get("media_uploads")  == ""

def add_metrics_to_db():
    db = MyDb()

    with open('manual_ig.csv', 'r') as csvfile:
        reader = csv.DictReader(csvfile)
        for artist in reader:
            if is_manually_added_ig(artist):
                load_xml(artist.get("ig_handle"))
                metrics_dict = get_metrics_from_xml()
                artist.update(
                    media_uploads=metrics_dict.get("media_uploads"),
                    followers=metrics_dict.get("followers"),
                    following=metrics_dict.get("following"),
                    engagement_rate=metrics_dict.get("engagement_rate"),
                    avg_likes=metrics_dict.get("avg_likes"),
                    avg_comments=metrics_dict.get("avg_comments")
                )
                print(artist)
                db.add_artist(artist)
# db = MyDb()
# db.get_db_as_csv()
add_metrics_to_db()