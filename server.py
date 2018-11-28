#!/usr/bin/python3
from flask import Flask, request, jsonify, render_template, make_response
from flask_restful import Resource, Api
from sqlalchemy import create_engine
from json import dumps
from euclidean import *
from pearson import *
import itertools as it

db_connect = create_engine('sqlite:///movies.db')
app = Flask(__name__, template_folder='templates')
api = Api(app)


# get all users
def getUsers():
    conn = db_connect.connect()
    query5 = conn.execute("select * from users")
    users = [i for i in query5.cursor.fetchall()]
    return users


class Welcome(Resource):
    def get(self):
        headers = {'Content-Type': 'text/html'}
        conn = db_connect.connect() # connect to database

        return make_response(render_template('index.html', users=getUsers()),200,headers)



class Ratings(Resource):
    def get(self):
        headers = {'Content-Type': 'text/html'}
        conn = db_connect.connect()
        query = conn.execute("select * from ratings")

        ratings = {'ratings': [i for i in query.cursor.fetchall()]}
        # get all users
        query5 = conn.execute("select * from users")
        users = [i for i in query5.cursor.fetchall()]
        return make_response(render_template('ratings.html', users=users, ratings=ratings), 200, headers)


class Username(Resource):
    def get(self, userid):
        USERID = userid
        headers = {'Content-Type': 'text/html'}
        conn = db_connect.connect()

        # Database calls
        #userA
        query = conn.execute("select * from ratings where userid =%d " %int(userid))
        userA = [i for i in query.cursor.fetchall()]
        # all ratings
        query4 = conn.execute("select * from ratings")
        ratings = [i for i in query4.cursor.fetchall()]
        # get all users
        query5 = conn.execute("select * from users")
        users = [i for i in query5.cursor.fetchall()]
        # username
        query3 = conn.execute("select * from users where id =%d " %int(userid))
        username = {'data': [dict(zip(tuple(query3.keys()), i)) for i in query3.cursor]}

        # create array
        similarities = []
        n = 0
        for user in users:
            query6 = conn.execute("select * from ratings where userid=%d " %int(user[0]))
            userX = [i for i in query6.cursor.fetchall()]

            if (user[0] != username['data'][0]['id']):
                similarities.append([user, euclidean(userA, userX)])


        def getSimScore(userid, sims):
            if userid < len(sims):
                return sims[userid][1]
            else:
                return 0

        ratingsWithWS = []
        # get weighted score (ws)
        # loop through ratings
        for rating in ratings:
            totalws = 0
            userid = rating[0] - 1
            ws = 0
            # get similarity for user
            simscore = getSimScore(userid, similarities)
            # multiply by rating to get weighted score
            ws = rating[2] * simscore
            # print("Current user:")
            # print(userid+1)
            # print("Current movie:")
            # print(rating[1])
            # print("Rated:")
            # print(rating[2])
            # print("Users simscore:")
            # print(simscore)
            # print("Weighted score:")
            # print(str(ws))

            # store important values in a dictionary
            ratingsWithWS.append({
            'userid': userid+1,
            'movie': rating[1],
            'rating': rating[2],
            'similarity': simscore,
            'ws': ws
            })

        similarities = similarities[:3]
        print("sims")

        # Sort similarities in reverse order
        newsims = []
        for sim in similarities:
            print(sim)
            newsims.append(tuple((sim[0][1], sim[1])))

        newsims = sorted(newsims, key=lambda x: x[1], reverse=True)


        # sort ratingsWithWS on film instead of userids
        newratings = sorted(ratingsWithWS, key=lambda k: k['movie'])

        # sum total ws for each movie, group:
        def get_ws(movie):
            return lambda x: x['ws'] if x['movie']==movie else 0

        def get_sim(movie):
            return lambda x: x['similarity'] if x['movie']==movie else 0

        # get sum of similarity for all users with matching movies
        movies = sorted(set(map(lambda x: x['movie'], newratings)))
        result = [{'movie':movie, 'sumsim': sum(map(get_sim(movie), newratings)), 'sumws':sum(map(get_ws(movie), newratings))} for movie in movies]


        def getTotalDividedBySumsim(movie):
            return lambda x: x['sumws']/x['sumsim'] if x['movie']==movie else 0
        # calculate total ws divided by sum of similarity
        # for every movie
        newmovies = sorted(set(map(lambda x: x['movie'], result)))
        newresult = [{'movie':movie, 'divbysim': round(sum(map(getTotalDividedBySumsim(movie), result)),4)} for movie in newmovies]

        # exclude movies already seen by user
        def getAlreadySeen(userid):
            #loop through ratings
            movies = []
            for rating in ratings:
                userid = int(userid)
                if rating[0] == userid and any(d['movie'] == rating[1] for d in newresult):
                    movies.append(rating[1])
            return movies

        alreadySeen = getAlreadySeen(USERID)
        newresult[:] = [d for d in newresult if d.get('movie') not in alreadySeen]

        newresult.sort(key = lambda x:x['divbysim'], reverse = True)

        recommended_movies = newresult[:3]

        return make_response(render_template('username.html',users=users, username=username, similarities=newsims, ratingsWithWS=newratings, recommended_movies=recommended_movies, algorithm="Euclidean Distance"), 200, headers)


class Pearson(Resource):
    def get(self, userid):
        USERID = userid
        headers = {'Content-Type': 'text/html'}
        conn = db_connect.connect()

        # Database calls
        #userA
        query = conn.execute("select * from ratings where userid =%d " %int(userid))
        userA = [i for i in query.cursor.fetchall()]
        # all ratings
        query4 = conn.execute("select * from ratings")
        ratings = [i for i in query4.cursor.fetchall()]
        # get all users
        query5 = conn.execute("select * from users")
        users = [i for i in query5.cursor.fetchall()]
        # username
        query3 = conn.execute("select * from users where id =%d " %int(userid))
        username = {'data': [dict(zip(tuple(query3.keys()), i)) for i in query3.cursor]}

        # Create a nested dictionary containing all critics and their recommendations
        # First create a list of critics
        print("critics")
        newcritics = [critic[0] for critic in users]
        print(newcritics)

        prefs = {}
        print("new dict:")
        for critic in newcritics:
            critic = str(critic)
            criticname = str(critic)
            critic = {}
            for rating in ratings:
                criticid = str(rating[0])
                if criticid == criticname:
                    critic[rating[1]] = rating[2]
            prefs[criticname] = critic

        print(prefs)

        usersent = str(userid)
        rankings, similarities = getRecommendations(prefs, usersent)
        print(rankings)

        newsims = []
        for key in similarities:
            intkey = int(key) - 1
            newkey = users[intkey][1]
            # print(newkey)
            # print(similarities[key])
            # similarities[newkey] = similarities.pop(key)

            print(newkey)
            newsims.append((similarities[key], newkey))

        print("newsims")
        print(newsims)

        newsims.sort( )
        newsims.reverse( )

        return make_response(render_template('pearson.html',users=users, username=username, similarities=newsims, recommended_movies=rankings, algorithm="Pearson Correlation"), 200, headers)


api.add_resource(Welcome, '/') # Route_1
api.add_resource(Ratings, '/ratings') # Route_2
api.add_resource(Username, '/users/<userid>') # Route_3
api.add_resource(Pearson, '/pearson/<userid>') # Route_4


if __name__ == '__main__':
     app.run()
