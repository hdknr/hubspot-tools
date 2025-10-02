import click


@click.group()
@click.pass_context
def blogs(ctx):
    pass


@blogs.command()
@click.pass_context
def list_blog(ctx):
    """ブログ一覧"""
    print("ブログ一覧")
