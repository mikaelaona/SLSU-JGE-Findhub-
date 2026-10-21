
import os
import secrets
from datetime import datetime
from functools import wraps

from flask import (
    Flask, render_template, request, redirect,
    url_for, flash, session, abort, make_response, jsonify
)
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import desc, or_


app = Flask(__name__)

app.config["SECRET_KEY"] = os.environ.get(
    "SECRET_KEY", "change-this-secret-key-before-deployment"
)
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
app.config["MAX_CONTENT_LENGTH"] = 5 * 1024 * 1024

database_url = os.environ.get("DATABASE_URL", "sqlite:///findhub.db")

if database_url.startswith("postgres://"):
    database_url = database_url.replace(
        "postgres://", "postgresql://", 1
    )

if database_url.startswith("postgresql://"):
    database_url = database_url.replace(
        "postgresql://", "postgresql+psycopg://", 1
    )

app.config["SQLALCHEMY_DATABASE_URI"] = database_url

db = SQLAlchemy(app)

ALLOWED_IMAGE_TYPES = {"image/jpeg", "image/png", "image/webp"}
VALID_STATUSES = {"Lost", "Found", "Returned"}


class Item(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    report_type = db.Column(db.String(20), nullable=False, default="Lost")
    item_name = db.Column(db.String(120), nullable=False)
    category = db.Column(db.String(80), nullable=False, default="Other")
    location = db.Column(db.String(150), nullable=False)
    date_reported = db.Column(db.String(20), nullable=False)
    reporter_name = db.Column(db.String(120), nullable=False)
    contact_info = db.Column(db.String(150), nullable=False)
    description = db.Column(db.Text, nullable=False)
    status = db.Column(db.String(20), nullable=False, default="Lost")
    image_data = db.Column(db.LargeBinary, nullable=True)
    image_mimetype = db.Column(db.String(80), nullable=True)
    created_at = db.Column(
        db.DateTime, nullable=False, default=datetime.utcnow
    )


def initialize_database():
    with app.app_context():
        db.create_all()


def get_csrf_token():
    if "csrf_token" not in session:
        session["csrf_token"] = secrets.token_urlsafe(32)
    return session["csrf_token"]


@app.context_processor
def inject_csrf_token():
    return {"csrf_token": get_csrf_token()}


@app.before_request
def validate_csrf():
    if request.method == "POST":
        submitted = request.form.get("csrf_token", "")
        expected = session.get("csrf_token", "")

        if (
            not expected
            or not submitted
            or not secrets.compare_digest(submitted, expected)
        ):
            abort(
                400,
                description="Session token expired. Reload the page and try again."
            )


def admin_required(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        if not session.get("is_admin"):
            flash("Please sign in to access the admin dashboard.", "warning")
            return redirect(url_for("admin_login"))
        return view(*args, **kwargs)
    return wrapped


@app.route("/")
def index():
    items = Item.query.order_by(desc(Item.created_at)).all()
    return render_template("home.html", items=items)


@app.route("/submit", methods=["POST"])
def submit_report():
    report_type = request.form.get("report_type", "").strip().title()
    item_name = request.form.get("item_name", "").strip()
    category = request.form.get("category", "Other").strip()
    location = request.form.get("location", "").strip()
    date_reported = request.form.get("date_reported", "").strip()
    reporter_name = request.form.get("reporter_name", "").strip()
    contact_info = request.form.get("contact_info", "").strip()
    description = request.form.get("description", "").strip()

    if report_type not in {"Lost", "Found"}:
        flash("Please select Lost Item or Found Item.", "error")
        return redirect(url_for("index") + "#report")

    if not all([
        item_name, category, location, date_reported,
        reporter_name, contact_info, description
    ]):
        flash("Please complete all required fields.", "error")
        return redirect(url_for("index") + "#report")

    image_data = None
    image_mimetype = None
    image = request.files.get("image")

    if image and image.filename:
        if image.mimetype not in ALLOWED_IMAGE_TYPES:
            flash("Upload a JPG, PNG, or WebP image.", "error")
            return redirect(url_for("index") + "#report")

        image_data = image.read()

        if len(image_data) > 5 * 1024 * 1024:
            flash("The image must be 5 MB or smaller.", "error")
            return redirect(url_for("index") + "#report")

        if image_data:
            image_mimetype = image.mimetype
        else:
            image_data = None

    item = Item(
        report_type=report_type,
        item_name=item_name,
        category=category,
        location=location,
        date_reported=date_reported,
        reporter_name=reporter_name,
        contact_info=contact_info,
        description=description,
        status=report_type,
        image_data=image_data,
        image_mimetype=image_mimetype,
    )

    try:
        db.session.add(item)
        db.session.commit()
        flash("Your report has been submitted successfully.", "success")
    except Exception:
        db.session.rollback()
        app.logger.exception("Could not save item report.")
        flash("Could not save your report. Please try again.", "error")

    return redirect(url_for("index") + "#items")


@app.route("/image/<int:item_id>")
def item_image(item_id):
    item = db.get_or_404(Item, item_id)

    if not item.image_data:
        abort(404)

    response = make_response(item.image_data)
    response.headers["Content-Type"] = (
        item.image_mimetype or "application/octet-stream"
    )
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["Cache-Control"] = "private, max-age=3600"
    return response


def search_items(query="", status="all"):
    items_query = Item.query

    if query:
        pattern = f"%{query}%"
        items_query = items_query.filter(
            or_(
                Item.item_name.ilike(pattern),
                Item.category.ilike(pattern),
                Item.location.ilike(pattern),
                Item.description.ilike(pattern),
            )
        )

    if status.lower() in {"lost", "found", "returned"}:
        items_query = items_query.filter(
            Item.status == status.title()
        )

    return items_query.order_by(desc(Item.created_at))


@app.route("/api/items")
def api_items():
    query = request.args.get("q", "").strip()[:100]
    status = request.args.get("status", "all").strip().lower()

    items = search_items(query, status).limit(200).all()

    return jsonify({
        "items": [
            {
                "id": item.id,
                "item_name": item.item_name,
                "category": item.category,
                "location": item.location,
                "date_reported": item.date_reported,
                "description": item.description,
                "status": item.status,
                "image_url": (
                    url_for("item_image", item_id=item.id)
                    if item.image_data else None
                ),
            }
            for item in items
        ],
        "count": len(items),
    })


@app.route("/admin/login", methods=["GET", "POST"])
def admin_login():
    if request.method == "POST":
        username = os.environ.get("ADMIN_USERNAME", "admin")
        password = os.environ.get(
            "ADMIN_PASSWORD", "change-this-password"
        )

        entered_username = request.form.get("username", "")
        entered_password = request.form.get("password", "")

        if (
            secrets.compare_digest(entered_username, username)
            and secrets.compare_digest(entered_password, password)
        ):
            session.clear()
            session["is_admin"] = True
            get_csrf_token()
            flash("Welcome to the admin dashboard.", "success")
            return redirect(url_for("admin_dashboard"))

        flash("Incorrect username or password.", "error")

    return render_template("admin_login.html")


@app.route("/admin/logout", methods=["POST"])
@admin_required
def admin_logout():
    session.clear()
    flash("You have been logged out.", "success")
    return redirect(url_for("index"))


@app.route("/admin")
@admin_required
def admin_dashboard():
    items = Item.query.order_by(desc(Item.created_at)).all()
    return render_template("admin_dashboard.html", items=items)


@app.route("/admin/items/<int:item_id>/status", methods=["POST"])
@admin_required
def update_item_status(item_id):
    item = db.get_or_404(Item, item_id)
    status = request.form.get("status", "").title()

    if status not in VALID_STATUSES:
        flash("Invalid status selected.", "error")
        return redirect(url_for("admin_dashboard"))

    try:
        item.status = status
        db.session.commit()
        flash(f'Status for "{item.item_name}" updated to {status}.', "success")
    except Exception:
        db.session.rollback()
        app.logger.exception("Could not update item status.")
        flash("Could not update the item. Please try again.", "error")

    return redirect(url_for("admin_dashboard"))


@app.route("/health")
def health():
    try:
        db.session.execute(db.select(1))
        return {"status": "ok", "database": "connected"}, 200
    except Exception:
        db.session.rollback()
        app.logger.exception("Database health check failed.")
        return {"status": "error", "database": "unavailable"}, 503


@app.errorhandler(400)
def bad_request(error):
    return render_template(
        "error.html",
        error_code=400,
        message=getattr(error, "description", "Bad request."),
    ), 400


@app.errorhandler(403)
def forbidden(error):
    return render_template(
        "error.html",
        error_code=403,
        message="You do not have permission to access this page.",
    ), 403


@app.errorhandler(404)
def not_found(error):
    return render_template(
        "error.html",
        error_code=404,
        message="The page or item you requested could not be found.",
    ), 404


@app.errorhandler(500)
def server_error(error):
    db.session.rollback()
    return render_template(
        "error.html",
        error_code=500,
        message="Something went wrong. Please try again later.",
    ), 500


# Create missing tables when Gunicorn imports this module.
initialize_database()


if __name__ == "__main__":
    app.run(
        debug=os.environ.get("FLASK_DEBUG") == "1",
        host="0.0.0.0",
        port=int(os.environ.get("PORT", 5000)),
    )
