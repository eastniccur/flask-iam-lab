#!/usr/bin/env python3

from flask import request, session
from flask_restful import Resource
from sqlalchemy.exc import IntegrityError

from config import app, db, api
from models import User, Recipe, UserSchema, RecipeSchema

user_schema = UserSchema()
recipe_schema = RecipeSchema()


def format_errors(error):
    if isinstance(error, (IntegrityError, ValueError)):
        message = str(error.orig if hasattr(error, 'orig') and error.orig is not None else error)
        return {'errors': [message]}
    return {'errors': [str(error)]}


class Signup(Resource):
    def post(self):
        data = request.get_json() or {}
        username = (data.get('username') or '').strip()
        password = data.get('password')

        if not username:
            return {'errors': ['Username is required.']}, 422
        if not password:
            return {'errors': ['Password is required.']}, 422

        user = User(username=username, image_url=data.get('image_url'), bio=data.get('bio'))
        user.password_hash = password

        try:
            db.session.add(user)
            db.session.commit()
        except (IntegrityError, ValueError) as exc:
            db.session.rollback()
            return format_errors(exc), 422

        session['user_id'] = user.id
        return user_schema.dump(user), 201


class CheckSession(Resource):
    def get(self):
        user_id = session.get('user_id')

        if not user_id:
            return {'error': 'Unauthorized'}, 401

        user = User.query.filter_by(id=user_id).first()

        if not user:
            session.pop('user_id', None)
            return {'error': 'Unauthorized'}, 401

        return user_schema.dump(user), 200


class Login(Resource):
    def post(self):
        data = request.get_json() or {}
        username = (data.get('username') or '').strip()
        password = data.get('password')

        user = User.query.filter_by(username=username).first()

        if not user or not user.authenticate(password):
            return {'error': 'Unauthorized'}, 401

        session['user_id'] = user.id
        return user_schema.dump(user), 200


class Logout(Resource):
    def delete(self):
        if not session.get('user_id'):
            return {'error': 'Unauthorized'}, 401

        session.pop('user_id', None)
        return {}, 204


class RecipeIndex(Resource):
    def get(self):
        user_id = session.get('user_id')

        if not user_id:
            return {'error': 'Unauthorized'}, 401

        recipes = Recipe.query.filter_by(user_id=user_id).all()
        return [recipe_schema.dump(recipe) for recipe in recipes], 200

    def post(self):
        user_id = session.get('user_id')

        if not user_id:
            return {'error': 'Unauthorized'}, 401

        data = request.get_json() or {}
        title = (data.get('title') or '').strip()
        instructions = data.get('instructions') or ''
        minutes_to_complete = data.get('minutes_to_complete')

        errors = []

        if not title:
            errors.append('Title is required.')
        if not instructions:
            errors.append('Instructions are required.')
        elif len(instructions) < 50:
            errors.append('Instructions must be at least 50 characters long.')
        if minutes_to_complete is None:
            errors.append('Minutes to complete is required.')

        if errors:
            return {'errors': errors}, 422

        recipe = Recipe(
            title=title,
            instructions=instructions,
            minutes_to_complete=minutes_to_complete,
            user_id=user_id,
        )

        try:
            db.session.add(recipe)
            db.session.commit()
        except (IntegrityError, ValueError) as exc:
            db.session.rollback()
            return format_errors(exc), 422

        return recipe_schema.dump(recipe), 201


api.add_resource(Signup, '/signup', endpoint='signup')
api.add_resource(CheckSession, '/check_session', endpoint='check_session')
api.add_resource(Login, '/login', endpoint='login')
api.add_resource(Logout, '/logout', endpoint='logout')
api.add_resource(RecipeIndex, '/recipes', endpoint='recipes')


with app.app_context():
    db.create_all()


if __name__ == '__main__':
    app.run(port=5555, debug=True)