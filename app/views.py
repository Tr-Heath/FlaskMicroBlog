from flask import render_template, flash, redirect, session, url_for, request, g
from flask.ext.login import login_user, logout_user, current_user, login_required
from app import app, db, lm, oid
from forms import LoginForm, EditForm, PostForm
from models import User, ROLE_USER, ROLE_ADMIN, Post
from datetime import datetime

@lm.user_loader
def load_user(id):
	return User.query.get(int(id)) #id is unicode

@app.before_request
def before_request():
	g.user = current_user
	if g.user.is_authenticated():
		g.user.last_seen = datetime.utcnow()
		db.session.add(g.user)
		db.session.commit()

@app.errorhandler(404)
def internal_error(error):
	return render_template('404.html'), 404

@app.errorhandler(500)
def internal_error(error):
	print 'Error happened, gonna rollback'
	db.session.rollback()
	return render_template('500.html'), 500

@app.route('/', methods = ['GET', 'POST'])

@app.route('/index', methods = ['GET', 'POST'])
@login_required
def index():
    form = PostForm()
    if form.validate_on_submit():
    	post = Post(body = form.post.data, timestamp = datetime.utcnow(), author = g.user)
    	db.session.add(post)
    	db.session.commit()
    	flash('Post is now live.')
    	return redirect(url_for('index'))
    posts = g.user.followed_posts().all()
    return render_template("index.html",
    	title = 'Home',
     	form = form,
     	posts = posts)

@app.route('/login', methods = ['GET', 'POST'])
@oid.loginhandler
def login():
	#global g is used by Flask to store and share data during the life of the request.
	if g.user is not None and g.user.is_authenticated():
		return redirect(url_for('index'))
	form = LoginForm()
	if form.validate_on_submit():
		session['remember_me'] = form.remember_me.data #flask.session, data is available in future requests from same client
		#flash used for debugging purposes for now
		#flash('Login requested for OpenID="' + form.openid.data + '", remember_me=' + str(form.remember_me.data))
		return oid.try_login(form.openid.data, ask_for = ['nickname', 'email'], ask_for_optional=[])
	return render_template('login.html', 
							title = 'Sign In', 
							form = form,
							providers = app.config['OPENID_PROVIDERS'])

@app.route('/user/<nickname>')
@login_required
def user(nickname):
	user = User.query.filter_by(nickname = nickname).first()
	if user == None:
		flash('User ' + nickname + ' not found.')
		return redirect(url_for('index'))
	posts = [
		{ 'author': user, 'body': 'Test post #1' },
		{ 'author': user, 'body': 'Test post #2' }
	]
	return render_template('user.html', user = user, posts = posts)

@oid.after_login
#resp contains info from the OpenID provider
def after_login(resp):
	if resp.email is None or resp.email == "":
		flash('Invalid login. Please try again.')
		return redirect(url_for('login'))
	user = User.query.filter_by(email = resp.email).first()
	if user is None:
		nickname = resp.nickname
		if nickname is None or nickname == "":
			nickname = resp.email.split('@')[0]
		nickname = User.make_unique_nickname(nickname)
		user = User(nickname = nickname, email = resp.email, role = ROLE_USER)
		db.session.add(user)
		db.session.commit()
		#Users should follow themselves by default to see their own posts
		db.session.add(user.follow(user))
		db.session.commit()
	remember_me = False
	if 'remember_me' in session:
		remember_me = session['remember_me']
		session.pop('remember_me', None)
	login_user(user, remember = remember_me)
	return redirect(request.args.get('next') or url_for('index'))

@app.route('/edit', methods = ['GET', 'POST'])
@login_required
def edit():
	form = EditForm(g.user.nickname)
	if form.validate_on_submit():
		g.user.nickname = form.nickname.data
		g.user.about_me = form.about_me.data
		db.session.add(g.user)
		db.session.commit()
		flash('Your changes have been saved.')
		return redirect(url_for('edit'))
	else:
		form.nickname.data = g.user.nickname
		form.about_me.data = g.user.about_me
	return render_template('edit.html', form = form)

@app.route('/logout')
def logout():
	logout_user()
	return redirect(url_for('index'))

@app.route('/follow/<nickname>')
@login_required
def follow(nickname):
	user = User.query.filter_by(nickname = nickname).first()
	if user == None:
		flash('User ' + nickname + ' not found.')
		return redirect(url_for('index'))
	if user == g.user:
		flash('You can\'t follow yourself!')
		return redirect(url_for('user', nickname = nickname))
	db.session.add(u)
	db.session.commit()
	flash('You are now following ' + nickname + '!')
	return redirect(url_for('user', nickname = nickname))

@app.route('/unfollow/<nickname>')
@login_required
def unfollow(nickname):
	user = User.query.filter_by(nickname = nickname).first()
	if user == None:
		flash('User ' + nickname + ' not found.')
		return redirect(url_for('index'))
	if user == g.user:
		flash('You can\'t unfollow yourself!')
		return redirect(url_for('user', nickname = nickname))
	u = g.user.unfollow(user)
	if u is None:
		flash('Cannot unfollow ' + nickname + '.')
		return redirect(url_for('user', nickname = nickname))
	db.session.add(u)
	db.session.commit()
	flash('You have stopped following ' + nickname + '.')
	return redirect(url_for('user', nickname = nickname))


