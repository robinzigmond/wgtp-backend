import json
from flask import Flask
from flask_cors import CORS
from boardgamegeek import BGGClient
from boardgamegeek.exceptions import BGGItemNotFoundError
from rq import Queue
from rq.job import Job
from worker import conn

q = Queue(connection=conn)

app = Flask(__name__)
CORS(app)

bgg = BGGClient(requests_per_minute=10)

@app.route("/result/<job_id>")
def get_result(job_id):
    job = Job.fetch(job_id, connection=conn)
    print("status: {}".format(job.get_status()))
    if job.get_status() == "failed":
        return json.dumps({"done": False, "failed": True})
    res = job.result
    if res:
        return json.dumps({"done": True, "result": json.loads(res)})
    else:
        return json.dumps({"done": False})

@app.route("/collection/<username>")
def get_collection(username):
    job = q.enqueue(queue_get_collection, username, job_timeout=300)
    return json.dumps({"job_id": job.id})

@app.route("/check_ratings/<username>/<game_list>")
def check_rating(username, game_list):
    job = q.enqueue(queue_check_rating, username, game_list, job_timeout=300)
    return json.dumps({"job_id": job.id})

def queue_get_collection(username):
    try:
        personal_stats = bgg.collection(username, own=True).items
    except BGGItemNotFoundError:
        print("user {} doesn't appear to exist".format(username))
        return json.dumps([])

    # split into chunks to avoid 414 URL too long error
    CHUNK_SIZE = 200

    chunks = []
    while len(personal_stats) > 0:
        new_chunk = []
        while (len(new_chunk) < CHUNK_SIZE) and (len(personal_stats) > 0):
            new_chunk.append(personal_stats.pop(0))
        chunks.append(new_chunk)

    collection = []
    for chunk in chunks:
        # get all games which are not expansions
        collection.extend([game.data() for game in bgg.game_list(game_id_list=[stats.id for stats in chunk])
                            if not game.data()["expands"]])

    print("user {} has {} games owned".format(username, len(collection)))
    return json.dumps(collection)

def queue_check_rating(username, game_list):
    try:
        games_in_collection = bgg.collection(username, rated=True).items
    except BGGItemNotFoundError:
        print("user {} doesn't appear to exist".format(username))
        return json.dumps(None)

    games_asked = list(map(int, game_list.split("-")))

    ratings = {}
    for game in games_in_collection:
        the_id = game.id
        if the_id in games_asked:
            print("user {} rates game {} (id {}) as {}".format(username, game.name, the_id, game.rating))
            ratings[the_id] = game.rating

    return json.dumps(ratings)
