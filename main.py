from functools import wraps

from flask import Flask, render_template, redirect, url_for, flash, abort
from flask_bootstrap import Bootstrap
from flask_ckeditor import CKEditor
from datetime import date

from sqlalchemy import ForeignKey
from werkzeug.security import generate_password_hash, check_password_hash
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.orm import relationship
from flask_login import UserMixin, login_user, LoginManager, login_required, current_user, logout_user
from forms import CreatePostForm, RegisterForm, LoginForm, CommentForm
from flask_gravatar import Gravatar

app = Flask(__name__)
app.config['SECRET_KEY'] = '8BYkEfBA6O6donzWlSihBXox7C0sKR6b'
ckeditor = CKEditor(app)
Bootstrap(app)

##CONNECT TO DB
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///blog.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

##INItIALIZE LOGIN

login_manager = LoginManager()
login_manager.init_app(app)

gravatar = Gravatar(app, size=100, rating='g', default='retro', force_default=False, force_lower=False, use_ssl=False, base_url=None)

##CONFIGURE TABLES

class BlogPost(db.Model):
    __tablename__ = "blog_posts"
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(250), unique=True, nullable=False)
    subtitle = db.Column(db.String(250), nullable=False)
    date = db.Column(db.String(250), nullable=False)
    body = db.Column(db.Text, nullable=False)
    img_url = db.Column(db.String(250), nullable=False)
    author_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    author = db.relationship("User", back_populates="posts")
    comments = db.relationship("Comment", back_populates="parent_post")

class User(UserMixin, db.Model):
    __tablename__ = "users"
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(100), nullable=False)
    password = db.Column(db.String(100), nullable=False)
    posts = db.relationship("BlogPost", back_populates="author")
    comments = db.relationship("Comment", back_populates="author")

class Comment(db.Model):
    __tablename__ = "comments"
    id = db.Column(db.Integer, primary_key=True)
    text = db.Column(db.Text, nullable=False)
    author_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    author = db.relationship("User", back_populates="comments")
    post_id = db.Column(db.Integer, db.ForeignKey('blog_posts.id'))
    parent_post = db.relationship("BlogPost", back_populates="comments")

with app.app_context():
    db.create_all()

def admin_only(function):
    @wraps(function)
    def decorated_function(*args,**kwargs):
        if current_user.id != 1:
            return abort(403)
        return function(*args,**kwargs)
    return decorated_function

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(user_id)

@app.route('/')
def get_all_posts():
    posts = BlogPost.query.all()
    return render_template("index.html", all_posts=posts,logged_in=current_user.is_authenticated)


@app.route('/register', methods=["GET","POST"])
def register():
    form = RegisterForm()
    if form.validate_on_submit():
        email = form.email.data
        if User.query.filter_by(email=email).first():
            flash("You've already signed up with that email, log in instead!", 'error')
            return redirect(url_for('login'))
        new_user = User(email=email,
                        password = generate_password_hash(form.password.data,method="pbkdf2:sha256",salt_length=8),
                        name=form.name.data)
        db.session.add(new_user)
        db.session.commit()
        login_user(user=new_user)
        return redirect(url_for('get_all_posts'))
    return render_template("register.html", form=form,logged_in=current_user.is_authenticated)


@app.route('/login', methods=["GET","POST"])
def login():
    form = LoginForm()
    if form.validate_on_submit():
        email = form.email.data
        user = User.query.filter_by(email=email).first()
        if not user:
            flash("Email not registered.",'error')
            return redirect(url_for('login'))
        if not check_password_hash(user.password,form.password.data):
            flash("Password incorrect.",'error')
            return redirect(url_for('login'))
        login_user(user)
        return redirect(url_for('get_all_posts'))
    return render_template("login.html",form=form,logged_in=current_user.is_authenticated)


@app.route('/logout')
def logout():
    logout_user()
    return redirect(url_for('get_all_posts'))


@app.route("/post/<int:post_id>",methods=["GET","POST"])
def show_post(post_id):
    form= CommentForm()
    requested_post = BlogPost.query.get(post_id)
    if form.validate_on_submit():
        if not current_user.is_authenticated:
            flash("You need to login or register to comment.")
            return redirect(url_for("login"))
        new_comment = Comment(text=form.body.data,
                              author=current_user,
                              parent_post=requested_post)
        db.session.add(new_comment)
        db.session.commit()

    return render_template("post.html", post=requested_post,logged_in=current_user.is_authenticated, form=form)


@app.route("/about")
def about():
    return render_template("about.html",logged_in=current_user.is_authenticated)


@app.route("/contact")
def contact():
    return render_template("contact.html")


@app.route("/new-post",methods=["GET","POST"])
@admin_only
def add_new_post():
    form = CreatePostForm()
    if form.validate_on_submit():
        new_post = BlogPost(
            title=form.title.data,
            subtitle=form.subtitle.data,
            body=form.body.data,
            img_url=form.img_url.data,
            author=current_user,
            date=date.today().strftime("%B %d, %Y")
        )
        db.session.add(new_post)
        db.session.commit()
        return redirect(url_for("get_all_posts"))
    return render_template("make-post.html", form=form)


@app.route("/edit-post/<int:post_id>",methods=["GET","POST"])
@admin_only
def edit_post(post_id):
    post = BlogPost.query.get(post_id)
    edit_form = CreatePostForm(
        title=post.title,
        subtitle=post.subtitle,
        img_url=post.img_url,
        author=post.author,
        body=post.body
    )
    if edit_form.validate_on_submit():
        post.title = edit_form.title.data
        post.subtitle = edit_form.subtitle.data
        post.img_url = edit_form.img_url.data
        post.author = edit_form.author.data
        post.body = edit_form.body.data
        db.session.commit()
        return redirect(url_for("show_post", post_id=post.id))

    return render_template("make-post.html", form=edit_form, logged_in=current_user.is_authenticated)


@app.route("/delete/<int:post_id>")
@admin_only
def delete_post(post_id):
    post_to_delete = BlogPost.query.get(post_id)
    db.session.delete(post_to_delete)
    db.session.commit()
    return redirect(url_for('get_all_posts'))


if __name__ == "__main__":
    app.run(host='0.0.0.0', port=5000)
