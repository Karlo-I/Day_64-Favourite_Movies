import sqlalchemy.exc
from flask import Flask, render_template, redirect, url_for, request, flash
from flask_bootstrap import Bootstrap5
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from sqlalchemy import Integer, String, Float
from flask_wtf import FlaskForm
from wtforms import StringField, SubmitField
from wtforms.validators import DataRequired
import requests, os
from dotenv import load_dotenv

load_dotenv()

MOVIE_DB_SEARCH_URL = "https://api.themoviedb.org/3/search/movie"
MOVIE_DB_INFO_URL = "https://api.themoviedb.org/3/movie"
MOVIE_DB_IMAGE_URL = "https://image.tmdb.org/t/p/w500"
MOVIE_DB_API_KEY = os.environ["API_KEY"]

'''
Red underlines? Install the required packages first: 
Open the Terminal in PyCharm (bottom left). 

On Windows type:
python -m pip install -r requirements.txt

On MacOS type:
pip3 install -r requirements.txt

This will install the packages from requirements.txt for this project.
'''

# Flask. Here we define our bakery, which is the web application itself. We use app = Flask(__name__) to
# create an instance of the Flask class and give it a name (__name__ is a special variable)
# It's like setting up the oven and workspace for baking
app = Flask(__name__)

# Secret key 🗝️ is important for app security, like having a secret recipe that no one else knows
app.config['SECRET_KEY'] = os.environ["SECRET_KEY"]
Bootstrap5(app) # Initialization of Flask Bootstrap extension

# CREATE DB and extension, and initialise
class Base(DeclarativeBase):
    pass

# Configure the app with the database URI
# This line sets the location 🗺️ of the database 🛢️ (a file named the_film_collection.db) and the type of database 🛢️
# (in this case SQLite). It's like determining where the ingredients will be stored for easy access.
app.config["SQLALCHEMY_DATABASE_URI"] = 'sqlite:///movies.db'

# CREATE DB 🛢, initialise the SQLAlchemy tool using db.init_app(app).
# It allows them to work together smoothly, like having a skilled baker who knows how to operate the oven
db = SQLAlchemy(model_class=Base)
db.init_app(app) # this only needs to run once, otherwise returns an error

# CREATE TABLE
# Here we define the model of the database ('Movie'🎞️). This model represents a single film 🎞️ in the database🛢️,
# with data such as title, year of production, description, rating, ranking, review, and image URL.
# Notice the difference in syntax (db.Column), first half is used in Day 88 Capstone
class Movie(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(250), unique=True, nullable=False)
    year = db.Column(db.Integer, nullable=False)
    description = db.Column(db.String(500), nullable=False)
    rating: Mapped[float] = mapped_column(Float, nullable=True)
    ranking: Mapped[int] = mapped_column(Integer, nullable=True)
    review: Mapped[str] = mapped_column(String(250), nullable=True)
    img_url: Mapped[str] = mapped_column(String(250), nullable=False)

# Flask-SQLAlchemy. Create tables 🪧 in the database 🛢️, but only if they don't exist yet.
# Provides the appropriate environment 🍀 for db.create_all().
# Tells the app to temporarily use the "app_context", which is necessary for communicating with the database 🛢️.
with app.app_context():
    # Checks whether the tables 🪧🪧🪧 in the database 🛢️ already exist.
    # If they don't, the code creates them.✅, if they do, the code does nothing.✖️
    db.create_all()

class RateMovieForm(FlaskForm):
    rating = StringField("Your Rating Out of 10 e.g. 7.5")
    review = StringField("Your Review")
    submit = SubmitField("Done")

class FindMovieForm(FlaskForm):
    title = StringField("Movie Title", validators=[DataRequired()])
    submit = SubmitField("Add Movie")

@app.route("/")
def home():
    # SQLAlchemy. Construct a query to retrieve data from the database.
    # The Result.scalars() method gets a list 📃 of results, .desc() provides the list in descending order
    result = db.session.execute(db.select(Movie).order_by(Movie.rating.desc()))
    all_movies = result.scalars().all() # convert ScalarResult to Python List

    rank = 1
    for movie in all_movies:
        movie.ranking = rank
        rank += 1
        db.session.commit()

    return render_template("index.html", movies=all_movies)

@app.route("/add", methods=["GET", "POST"])
def add_movie():
    form = FindMovieForm()

    if form.validate_on_submit():
        movie_title = form.title.data
        response = requests.get(MOVIE_DB_SEARCH_URL, params={"api_key": MOVIE_DB_API_KEY, "query": movie_title})
        data = response.json()["results"]
        return render_template("select.html", options=data)

    return render_template("add.html", form=form)

@app.route("/edit", methods=["GET", "POST"])
def rate_movie():
    form = RateMovieForm()
    movie_id = request.args.get("id")
    movie = db.get_or_404(Movie, movie_id)
    if form.validate_on_submit():
        movie.rating = float(form.rating.data)
        movie.review = form.review.data
        db.session.commit()
        return redirect(url_for("home"))
    return render_template("edit.html", movie=movie, form=form)

@app.route("/delete")
def delete_movie():
    movie_id = request.args.get("id")
    movie = db.get_or_404(Movie, movie_id)
    if request.method == "POST":
        db.session.delete(movie)
        db.session.commit()
        return redirect(url_for("home"))

    # Ensures a movies is not deleted inadvertently
    flash('You are about to delete this movie.')
    return render_template("delete.html", movie=movie)

@app.route("/find")
def find_movie():
    movie_api_id = request.args.get("id")
    if movie_api_id:
        movie_api_url = f"{MOVIE_DB_INFO_URL}/{movie_api_id}"
        # The language parameter is optional, if you were making the website for a different audience
        response = requests.get(movie_api_url, params={"api_key": MOVIE_DB_API_KEY, "language": "en-US"})
        data = response.json()
        new_movie = Movie(
            title=data["title"],
            # The data in release_date includes month and day, we will want to get rid of.
            year=data["release_date"].split("-")[0],
            # img_url API Documentation: https://developer.themoviedb.org/docs/image-basics
            img_url=f"{MOVIE_DB_IMAGE_URL}{data['poster_path']}",
            description=data["overview"]
        )
        db.session.add(new_movie)
        db.session.commit()
        return redirect(url_for("rate_movie", id=new_movie.id))

if __name__ == '__main__':
    app.run(debug=True)
