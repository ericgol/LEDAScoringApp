"""LEDA Drone Scoring - Flask Application Factory."""

import os
from flask import Flask
from app.config import Config


def create_app(config_class=Config):
    """Create and configure the Flask application."""
    app = Flask(__name__)
    app.config.from_object(config_class)

    # Ensure local upload directory exists for dev mode
    os.makedirs(app.config["LOCAL_UPLOAD_DIR"], exist_ok=True)
    os.makedirs(app.config["COURSE_DATA_DIR"], exist_ok=True)

    # Register blueprints
    from app.routes.upload import upload_bp
    from app.routes.scoring import scoring_bp
    from app.routes.courses import courses_bp

    app.register_blueprint(upload_bp)
    app.register_blueprint(scoring_bp)
    app.register_blueprint(courses_bp)

    # Register main page route
    @app.route("/")
    def index():
        from flask import render_template
        from app.models.course import get_all_courses
        courses = get_all_courses()
        return render_template("index.html", courses=courses)

    return app
