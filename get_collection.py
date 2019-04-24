import json
from flask import Flask
from flask_cors import CORS
from boardgamegeek import BGGClient
from boardgamegeek.exceptions import BGGItemNotFoundError

app = Flask(__name__)
CORS(app)

bgg = BGGClient(requests_per_minute=10)

@app.route("/collection/<username>")
def get_collection(username):
    try:
        personal_stats = bgg.collection(username, own=True).items
    except BGGItemNotFoundError:
        print("user {} doesn't appear to exist".format(username))
        return json.dumps([])
    global_stats = [game.data() for game in bgg.game_list(game_id_list=[stats.id for stats in personal_stats])]
    collection = []
    for game in global_stats:
        # remove all games which are not "standalone"
        if game["expands"]:
            continue
        game_dict = game
        for my_game in personal_stats:
            if (my_game.id == game["id"]):
                game_dict["my_rating"] = my_game.rating
                break
        collection.append(game_dict)

    print("user {} has {} games owned".format(username, len(collection)))
    return json.dumps(collection)

@app.route("/check_ratings/<username>/<game_list>")
def check_rating(username, game_list):
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
