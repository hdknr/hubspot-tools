import click


@click.group()
@click.pass_context
def main(ctx):
    ctx.ensure_object(dict)


if __name__ == "__main__":
    main()
