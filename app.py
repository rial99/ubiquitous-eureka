import os
from flask import Flask, render_template, flash, redirect, url_for, session, logging, request, Markup, send_from_directory
from flask_mysqldb import MySQL
from flask_wtf import FlaskForm
from wtforms import Form, StringField, TextAreaField, PasswordField, validators, SubmitField
from wtforms.validators import DataRequired
from passlib.hash import sha256_crypt
from functools import wraps
from flask_ckeditor import CKEditor, CKEditorField
basedir = os.path.abspath(os.path.dirname(__file__))
# flask-ckeditor configuration
app = Flask(__name__)
app.config['CKEDITOR_SERVE_LOCAL'] = True
app.config['CKEDITOR_HEIGHT'] = 400
app.config['CKEDITOR_FILE_UPLOADER'] = 'upload'
app.config['UPLOADED_PATH'] = basedir + '/uploads'
#init ckeditor
ckeditor = CKEditor(app)
#config MySQL
app.config['MYSQL_HOST'] = 'localhost'
app.config['MYSQL_USER'] = 'root'
app.config['MYSQL_PASSWORD'] = '143*hammer'
app.config['MYSQL_DB'] = 'myflaskapp'
app.config['MYSQL_CURSORCLASS'] = 'DictCursor'
#init MySQL
mysql = MySQL(app)

# Articles = Articles()

@app.route('/')
def index():
    return render_template("home.html")

@app.route('/about')
def about():
    return render_template('about.html')

@app.route('/articles')
def articles():
    #create cursor
    cur = mysql.connection.cursor()

    #get articles
    result = cur.execute("SELECT * FROM articles ORDER BY create_date DESC")

    articles = cur.fetchall()

    if result > 0:
        return render_template('articles.html',articles=articles)
    else:
        msg = 'NO ARTICLES FOUND'
        return render_template('articles.html',articles=articles)
    #close connection
    cur.close()


@app.route('/article/<string:id>')
def article(id):
    #create cursor
    cur = mysql.connection.cursor()

    #get articles
    result = cur.execute("SELECT * FROM articles WHERE id = %s",[id])

    article = cur.fetchone()

    return render_template('article.html', article=article)

class RegisterForm(Form):
    name = StringField('Name', [validators.Length(min=1,max=50)])
    username = StringField('Username', [validators.Length(min=4,max=25)])
    email = StringField('Email', [validators.Length(min=6,max=50)])
    password = PasswordField('password',[
        validators.DataRequired(),
        validators.EqualTo('confirm',message = 'Passwords do not match')
    ])
    confirm = PasswordField('Confirm Password')

@app.route('/register',methods=['GET','POST'])
def register():
    form = RegisterForm(request.form)
    if request.method == 'POST' and form.validate():
        name = form.name.data
        email = form.email.data
        username = form.username.data
        password = sha256_crypt.encrypt(str(form.password.data))

        #cursor handling
        cur = mysql.connection.cursor()

        cur.execute("INSERT INTO users(name,email,username,password) VALUES(%s, %s, %s, %s)",(name,email,username,password))

        #commit to db
        mysql.connection.commit()
        #close connection
        cur.close()
        flash('you are now registered and can log in' ,'success')
        return redirect(url_for('login'))

    return render_template('register.html',form=form)
# User login
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        # Get Form Fields
        username = request.form['username']
        password_candidate = request.form['password']

        # Create cursor
        cur = mysql.connection.cursor()

        # Get user by username
        result = cur.execute("SELECT * FROM users WHERE username = %s", [username])

        if result > 0:
            # Get stored hash
            data = cur.fetchone()#GETS THE FIRST QUERY
            password = data['password']

            # Compare Passwords
            if sha256_crypt.verify(password_candidate, password):
                # Passed
                session['logged_in'] = True
                session['username'] = username
                app.logger.info('password matched')
                flash('You are now logged in', 'success')
                return redirect(url_for('dashboard'))
            else:
                error = 'Invalid login'
                app.logger.info('PASSWORD MISMATCH')
                return render_template('login.html', error=error)
            # Close connection
            cur.close()
        else:
            error = 'Username not found'
            app.logger.info('NO USER')
            return render_template('login.html', error=error)

    return render_template('login.html')

#check if user is logged in
def is_logged_in(f):
    @wraps(f)
    def wrap(*args, **kwargs):
        if 'logged_in' in session:
            return f(*args, **kwargs)
        else:
            flash('Unauthorised, please login','danger')
            return redirect(url_for('login'))
    return wrap

@app.route('/logout')
@is_logged_in
def logout():
    session.clear()
    flash('you are now logged out ','success')
    return redirect(url_for('login'))

@app.route('/dashboard')
@is_logged_in
def dashboard():
    #create cursor
    cur = mysql.connection.cursor()

    #get articles
    result = cur.execute("SELECT * FROM articles WHERE author=%s",[session['username']])

    articles = cur.fetchall()

    if result > 0:
        return render_template('dashboard.html',articles=articles)
    else:
        msg = 'NO ARTICLES FOUND'
        return render_template('dashboard.html',articles=articles,error=msg)
    #close connection
    cur.close()

#article form class
class ArticleForm(FlaskForm):
    title = StringField('Title', [validators.Length(min=1,max=200)])
    # body = TextAreaField('Body', [validators.Length(min=30)])
    body = CKEditorField('Body', validators=[DataRequired()])


#add article
@app.route('/add_article',methods=['GET','POST'])
@is_logged_in
def add_article():
    form = ArticleForm()
    # form = PostForm()

    if form.validate_on_submit():
        title = form.title.data
        body = form.body.data

        #create cursor
        cur = mysql.connection.cursor()
        #execute
        cur.execute("INSERT INTO articles(title, body, author) VALUES(%s, %s, %s)",(title, body, session['username']))

        #commit to db
        mysql.connection.commit()

        #close connection
        cur.close()

        flash('Article Created','success')

        return redirect(url_for('dashboard'))

    return render_template('add_article.html', form=form)

#edit article
@app.route('/edit_article/<string:id>',methods=['GET','POST'])
@is_logged_in
def edit_article(id):
    #create cursor
    cur = mysql.connection.cursor()
    #get articles by id
    result = cur.execute("SELECT * FROM articles where id = %s", [id])

    article = cur.fetchone()
    #get form
    form = ArticleForm()
    #populate article from fields
    form.title.data = article['title']
    form.body.data = article['body']
    # app.logger.info(form.title.data)
    if form.validate_on_submit():
        title = request.form['title']
        body = request.form['body']
        # app.logger.info(form.title.data)
        #create cursor
        cur = mysql.connection.cursor()
        #execute
        cur.execute("UPDATE articles SET title=%s, body=%s WHERE id = %s", (title,body,[id]))

        #commit to db
        mysql.connection.commit()

        #close connection
        cur.close()

        flash('Article updated','success')

        return redirect(url_for('dashboard')) ##

    return render_template('edit_article.html', form=form)

@app.route('/files/<filename>')
def files(filename):
	path = app.config['UPLOADED_PATH']
	return send_from_directory(path, filename)


@app.route('/upload', methods=['POST'])
@ckeditor.uploader
def upload():
	f = request.files.get('upload')
	f.save(os.path.join(app.config['UPLOADED_PATH'], f.filename))
	url = url_for('files', filename=f.filename)
	return url


#delete article
@app.route('/delete_article/<string:id>',methods=['POST'])
@is_logged_in
def delete_article(id):
    #create cursor
    cur = mysql.connection.cursor()
    #execute
    cur.execute("DELETE FROM articles WHERE id = %s",[id])
    #commit to db
    mysql.connection.commit()

    #close connection
    cur.close()
    flash('Article Deleted','success')

    return redirect(url_for('dashboard'))



if __name__ == '__main__':
    app.secret_key = 'my secret key'
    app.run(host='0.0.0.0',debug=True,port=80,threaded=True)
