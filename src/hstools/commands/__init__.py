import click

from hstools.commands import blogs


@click.group()
@click.pass_context
def main(ctx):
    ctx.ensure_object(dict)


main.add_command(blogs.blogs)

if __name__ == "__main__":
    main()
