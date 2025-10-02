import click


@click.group()
@click.option("--tf_output", "-to", default=None)
@click.pass_context
def main(ctx, tf_output):
    ctx.ensure_object(dict)


if __name__ == "__main__":
    main()
