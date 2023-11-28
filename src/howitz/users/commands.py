import sys
import click
from flask.cli import AppGroup, with_appcontext
from flask import current_app

from howitz.users.model import User


user_cli = AppGroup("user")


@user_cli.command("create")
@click.argument("username")
@click.argument("password")
@click.argument("token")
@with_appcontext
def create_user(username, password, token):
    with current_app.app_context():
        existing_user = current_app.database.get(username)
        if existing_user:
            click.echo(f'User {username} already exists, aborting', err=True)
            sys.exit(1)
        new_user = User(username=username, password=password, token=token)
        user = current_app.database.add(new_user)
        if not user:
            click.echo(f'User {username} could not be created, aborting', err=True)
            sys.exit(1)
        click.echo(f'User {username} was successfully created')
        sys.exit(0)


@user_cli.command("update")
@click.argument("username")
@click.option("-p", "--password")
@click.option("-t", "--token")
@with_appcontext
def update_user(username, password, token):
    with current_app.app_context():
        if not (password or token):
            click.echo(f'Neither token nor password given, aborting', err=True)
            sys.exit(1)
        user = current_app.database.get(username)
        if not user:
            click.echo(f'User {username} not found, nothing to update', err=True)
            sys.exit(1)
        user.token = token if token else user.token
        user.password = password if password else user.password
        updated_user = current_app.database.update(user)
        if updated_user:
            click.echo(f'User {username} was successfully updated')
            sys.exit(0)
        click.echo(f'User {username} could not be updated', err=True)
        sys.exit(1)


@user_cli.command("delete")
@click.argument("username")
@with_appcontext
def delete_user(username):
    with current_app.app_context():
        user = current_app.database.get(username)
        if not user:
            click.echo(f'User {username} not found, nothing to remove', err=True)
            sys.exit(1)
        user = current_app.database.remove(username)
        user = current_app.database.get(username)
        if user is None:
            click.echo(f'User {username} removed')
            sys.exit(0)


@user_cli.command("list")
@with_appcontext
def list_users():
    with current_app.app_context():
        users = current_app.database.get_all()
        if not users:
            click.echo(f'No users found, aborting', err=True)
            sys.exit(1)
        for user in users:
            click.echo(user.username)
        sys.exit(0)
