import os
import sqlite3
from flask import Flask, request, session, g, redirect, url_for, abort, \
    render_template, flash
from time import time

app = Flask(__name__)
app.config.from_object(__name__)

# Load default config and override config from an environment variable
app.config.update(dict(
    DATABASE=os.path.join(app.root_path, 'db', 'cards.db'),
    SECRET_KEY='development key',
    USERNAME='admin',
    PASSWORD='default'
))
app.config.from_envvar('CARDS_SETTINGS', silent=True)


def connect_db():
    rv = sqlite3.connect(app.config['DATABASE'])
    rv.row_factory = sqlite3.Row
    return rv


def init_db():
    db = get_db()
    with app.open_resource('data/schema.sql', mode='r') as f:
        db.cursor().executescript(f.read())
    db.commit()


def get_db():
    """Opens a new database connection if there is none yet for the
    current application context.
    """
    if not hasattr(g, 'sqlite_db'):
        g.sqlite_db = connect_db()
    return g.sqlite_db


@app.teardown_appcontext
def close_db(error):
    """Closes the database again at the end of the request."""
    if hasattr(g, 'sqlite_db'):
        g.sqlite_db.close()

# fix table column
def add_column(column_name, type):
    db = get_db()
    cursor = db.execute('SELECT * FROM cards LIMIT 1')
    card = cursor.fetchone()
    try:
        card.keys().index(column_name)
    except ValueError:
        command = 'ALTER TABLE cards ADD COLUMN ' + column_name + ' ' + type
        db.execute(command)
        db.commit()

def alter_db():
    add_column('weight', 'integer default 0')
    add_column('language', 'text')
    add_column('timestamp', 'integer')

# -----------------------------------------------------------

# Uncomment and use this to initialize database, then comment it
#   You can rerun it to pave the database and start over
# @app.route('/initdb')
# def initdb():
#     init_db()
#     return 'Initialized the database.'

@app.route('/alterdb')
def alterdb():
    if not session.get('logged_in'):
        return redirect(url_for('login'))
    alter_db()
    return redirect(url_for('cards'))

@app.route('/')
def index():
    if session.get('logged_in'):
        return redirect(url_for('general'))
    else:
        return redirect(url_for('login'))

@app.route('/add_card')
def add_card():
    if not session.get('logged_in'):
        return redirect(url_for('login'))
    return render_template('add_card.html')

@app.route('/cards')
def cards():
    if not session.get('logged_in'):
        return redirect(url_for('login'))
    db = get_db()
    query = '''
        SELECT id, type, front, back, known, weight, language
        FROM cards
        ORDER BY id DESC
    '''
    cur = db.execute(query)
    cards = cur.fetchall()
    return render_template('cards.html', cards=cards, filter_name="all")


@app.route('/filter_cards/<filter_name>')
def filter_cards(filter_name):
    if not session.get('logged_in'):
        return redirect(url_for('login'))

    filters = {
        "all":      "where 1 = 1",
        "general":  "where type = 1",
        "code":     "where type = 2",
        "known":    "where known = 1",
        "unknown":  "where known = 0",
    }

    query = filters.get(filter_name)

    if not query:
        return redirect(url_for('cards'))

    db = get_db()
    fullquery = "SELECT id, type, front, back, known, weight, language FROM cards " + query + " ORDER BY id DESC"
    cur = db.execute(fullquery)
    cards = cur.fetchall()
    return render_template('cards.html', cards=cards, filter_name=filter_name)


@app.route('/add', methods=['POST'])
def add():
    if not session.get('logged_in'):
        return redirect(url_for('login'))
    db = get_db()
    db.execute('INSERT INTO cards (type, front, back, weight, language, timestamp) VALUES (?, ?, ?, ?, ?, ?)',
               [request.form['type'],
                request.form['front'],
                request.form['back'],
                request.form['weight'],
                request.form['language'],
                int(time() * 1000)
                ])
    db.commit()
    flash('New card was successfully added.')
    return redirect(url_for('add_card'))


@app.route('/edit/<card_id>')
def edit(card_id):
    if not session.get('logged_in'):
        return redirect(url_for('login'))
    db = get_db()
    query = '''
        SELECT id, type, front, back, known, weight, language
        FROM cards
        WHERE id = ?
    '''
    cur = db.execute(query, [card_id])
    card = cur.fetchone()
    return render_template('edit.html', card=card)


@app.route('/edit_card', methods=['POST'])
def edit_card():
    if not session.get('logged_in'):
        return redirect(url_for('login'))
    selected = request.form.getlist('known')
    known = bool(selected)
    db = get_db()
    command = '''
        UPDATE cards
        SET
          type = ?,
          front = ?,
          back = ?,
          known = ?,
          weight = ?,
          language = ?
        WHERE id = ?
    '''
    db.execute(command,
               [request.form['type'],
                request.form['front'],
                request.form['back'],
                known,
                request.form['weight'],
                request.form['language'],
                request.form['card_id']
                ])
    db.commit()
    flash('Card saved.')
    return redirect(url_for('cards'))


@app.route('/delete/<card_id>')
def delete(card_id):
    if not session.get('logged_in'):
        return redirect(url_for('login'))
    db = get_db()
    db.execute('DELETE FROM cards WHERE id = ?', [card_id])
    db.commit()
    flash('Card deleted.')
    return redirect(url_for('cards'))

@app.route('/within_a_day')
def within_a_day():
    return memorize("within_a_day", None)

def get_cards_within_a_day(len = 1):
    now = int(time() * 1000)
    left = now - 24 * 60 * 60 * 1000

    db = get_db()
    query = '''
        SELECT *
        FROM cards
        where timestamp >= ? and timestamp <= ?
        ORDER BY RANDOM()
        LIMIT ?
    '''
    cards = db.execute(query, [left, now, len])
    return cards

@app.route('/general')
@app.route('/general/<card_id>')
def general(card_id=None):
    return memorize("general", card_id)


@app.route('/reset')
def reset():
    if not session.get('logged_in'):
        return redirect(url_for('login'))
    reset_card_known();
    return redirect(url_for('general'))

@app.route('/code')
@app.route('/code/<card_id>')
def code(card_id=None):
    return memorize("code", card_id)

def reset_card_known():
    db = get_db()
    query = '''
        UPDATE cards
        SET known = 0
        WHERE known = 1
    '''
    db.execute(query)
    db.commit()

def memorize(card_type, card_id):
    if card_type == "general":
        type = 1
    elif card_type == "code":
        type = 2
    elif card_type == "within_a_day":
        type = -1

    if type != None:
        cards_len = 0

        if card_id:
            card = get_card_by_id(card_id)
        else:
            card = get_cards(type, 1).fetchone()
            cards_len = len(get_cards(type, 2).fetchall())

        if not card:
            flash("You've learned all the " + card_type + " cards.")
            return redirect(url_for('cards'))

        short_answer = (len(card['back']) < 75)
        return render_template('memorize.html',
                            card=card,
                            card_type=card_type,
                            short_answer=short_answer,
                            cards_len=cards_len
                            )
    else:
        return redirect(url_for('cards'))

def get_cards_by_type(type, len = 2):
    db = get_db()
    query = '''
      SELECT
        *
      FROM cards
      WHERE
        type = ?
        and known = 0
      ORDER BY RANDOM()
      LIMIT ?
    '''

    cur = db.execute(query, [type, len])
    return cur


def get_cards(type, len = 1):
    if type == -1:
        return get_cards_within_a_day(len)
    return get_cards_by_type(type, len)

def get_card_by_id(card_id):
    db = get_db()

    query = '''
      SELECT
        *
      FROM cards
      WHERE
        id = ?
      LIMIT 1
    '''

    cur = db.execute(query, [card_id])
    return cur.fetchone()


@app.route('/mark_known/<card_id>/<card_type>')
def mark_known(card_id, card_type):
    if not session.get('logged_in'):
        return redirect(url_for('login'))
    db = get_db()
    db.execute('UPDATE cards SET known = 1 WHERE id = ?', [card_id])
    db.commit()
    flash('Card marked as known.')
    return redirect(url_for(card_type))


@app.route('/login', methods=['GET', 'POST'])
def login():
    error = None
    if request.method == 'POST':
        if request.form['username'] != app.config['USERNAME']:
            error = 'Invalid username or password!'
        elif request.form['password'] != app.config['PASSWORD']:
            error = 'Invalid username or password!'
        else:
            session['logged_in'] = True
            session.permanent = True  # stay logged in
            return redirect(url_for('cards'))
    return render_template('login.html', error=error)


@app.route('/logout')
def logout():
    session.pop('logged_in', None)
    flash("You've logged out")
    return redirect(url_for('index'))


if __name__ == '__main__':
    app.run(host='0.0.0.0')
