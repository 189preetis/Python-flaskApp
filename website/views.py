from flask import Blueprint, render_template, request, redirect, url_for, flash, abort, session
from flask_login import login_required, current_user
from jinja2 import TemplateNotFound
from .models import Notes, Public_Notes, Users
from . import db
from secrets import token_urlsafe 
from datetime import datetime
from pytz import timezone
import requests

views = Blueprint('views',__name__)
__PUBLIC_NOTE_KEY__ = 20
DATETIME_FORMAT = "%d %m %Y %I:%M:%S %p"

@views.route('/')
def home():
    return render_template('index.html')

def set_timezone(ip):
        if not session.get('timezone'):
                    tz = requests.get(f'http://ip-api.com/json/{ip}').json()

                            if tz['status'] == 'fail':
                                        # set Default Timezone
                                                    session['timezone'] = 'Asia/Kolkata'
                                                return False

                                                                    # Set user Timezone as string (not as timezone object)
                                 session['timezone'] = tz['timezone']
                                        return True


@views.route('/notes')
def notes():
    set_timezone(request.remote_addr)

    if not current_user.is_authenticated:
        flash("login to view Notes", "info")
        return redirect(url_for("auth.login_page"))

    search_value = request.args.get('search-value')
    if search_value:
        notes = db.session.query(Notes,Public_Notes).join(Public_Notes, Public_Notes.Id == Notes.note_id, isouter=True).filter(Notes.user_id == current_user.id).filter(Notes.title.contains(search_value) | Notes.body.contains(search_value)).order_by(Notes.update_date.desc())
        return render_template('main-page.html', notes=notes, search_value=search_value)

    notes = db.session.query(Notes,Public_Notes).join(Public_Notes, Public_Notes.Id == Notes.note_id, isouter=True).filter(Notes.user_id == current_user.id)

    return render_template('main-page.html', notes=notes)

@views.route('/shared')
def shared():
    if not current_user.is_authenticated:
        flash("login to view Notes", "info")
        return redirect(url_for("auth.login_page"))

    notes = db.session.query(Notes,Public_Notes).join(Public_Notes, Public_Notes.Id == Notes.note_id).filter(Notes.user_id == current_user.id)

    return render_template('main-page.html', notes=notes, for_shared=True)

@views.route('/notes/<noteid>')
def note(noteid):
    if not current_user.is_authenticated:
        flash("login to view Notes", "info")
        return redirect(url_for("auth.login_page"))

    note = Notes.query.get(noteid)
    if note.user_id == current_user.id:
        if note.is_public:
            public_note_ = Public_Notes.query.filter_by(Id=noteid).first().slug
        else:
            public_note_ = None
        return render_template('note-private.html',note=note, note_key=public_note_)
    else:
        return abort(404)

@views.route('/add-note', methods=['GET', 'POST'])
@login_required
def add_note_page():
    if request.method == 'POST':

        is_public = 1 if request.form.get('is-public') == 'on' else 0

        note = Notes(
            title = request.form.get('note-title'),
            body = request.form.get('note-body'),
            is_public = is_public,
            update_date = datetime.now(timezone(session.get('timezone'))).strftime(DATETIME_FORMAT),
            user_id = current_user.id
        )
        db.session.add(note)
        db.session.commit()

        if is_public:        
            pnote = Public_Notes(Id=note.note_id, slug=token_urlsafe(__PUBLIC_NOTE_KEY__))
            db.session.add(pnote)
            db.session.commit()

        return redirect(url_for('views.notes'))
    else:
        return render_template('add-note.html')

@views.route('/edit-note/<noteid>', methods=['GET','POST'])
@login_required
def edit_page_page(noteid):
    if request.method == 'POST':
        is_public = 1 if request.form.get('is-public') == 'on' else 0

        note = Notes.query.get(noteid)
        if note.user_id == current_user.id:
            if is_public != note.is_public:
                # Add
                if is_public:
                    pnote = Public_Notes(Id=note.note_id, slug=token_urlsafe(__PUBLIC_NOTE_KEY__))
                    db.session.add(pnote)
                    db.session.commit()
                else:
                    # remove
                    pnote = Public_Notes.query.filter_by(Id=noteid).first()
                    db.session.delete(pnote)
                    db.session.commit()

            note.title = request.form.get('note-title')
            note.body = request.form.get('note-body')
            note.is_public = is_public
            note.update_date = datetime.now(timezone(session.get('timezone'))).strftime(DATETIME_FORMAT)

            db.session.commit()

            return redirect(url_for('views.notes') + f'/{note.note_id}')
        else:
            return abort(401)
    else:
        note = Notes.query.get(noteid)
        if note.user_id == current_user.id:
            checked = "checked" if note.is_public else "unchecked"
            return render_template('edit-note.html', note=note, checked=checked)
        else:
            return abort(404)

@views.route('/delete/<noteid>')
@login_required
def delete_note(noteid):
    note = Notes.query.get(noteid)
    if note.user_id == current_user.id:
        if note.is_public:
            pnote = Public_Notes.query.filter_by(Id=noteid).first()
            db.session.delete(pnote)
            db.session.commit()
        db.session.delete(note)
        db.session.commit()

        return redirect(url_for('views.notes'))
    else:
        return abort(404)

@views.route('/public/<note_key>')
def public_note(note_key):
    public_note_ = Public_Notes.query.get(note_key)
    if public_note_:
        note = Notes.query.get(public_note_.Id)
        return render_template('note-public.html', note=note, note_key=note_key)
    else:
        return abort(404)

@views.route('/about')
def about():
    return render_template('about-page.html')
