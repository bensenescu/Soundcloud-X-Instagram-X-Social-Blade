import firebase_admin
from firebase_admin import credentials
from firebase_admin import firestore
import csv
class MyDb:
    def __init__(self):
        # Use the application default credentials
        cred = credentials.Certificate("./soundcloud-scraper-firebase-adminsdk-tsxsi-82b9347dd3.json")
        firebase_admin.initialize_app(cred)

        self.db_coll = firestore.client().collection(u'artists')

    def add_artist(self, soundcloud_name, song_name, song_listens, genre, ig_handle):
        self.db_coll.document(soundcloud_name).set({
            u'soundcloud_name': soundcloud_name,
            u'song_name': song_name,
            u'song_listens': song_listens,
            u'genre': genre,
            u'timestamp': firestore.SERVER_TIMESTAMP,
            u'ig_handle': ig_handle,
        })

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



db = MyDb()
db.get_db_as_csv()