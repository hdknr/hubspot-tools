import click
import yaml

from src.hstools.commands import html


def load_ymal(path):
    with open(path) as input:
        config = yaml.safe_load(input)
        return config
    return None


def get_access_token(config, portal):
    potal_data = next(filter(lambda i: i["name"] == portal, config["portals"]), None)
    return potal_data and potal_data["auth"]["tokenInfo"]["accessToken"]


@click.group()
@click.argument("src_portal")
@click.option("--dst_portal", "-d", default=None)
@click.option("--config", default="hubspot.config.yml")
@click.pass_context
def main(ctx, src_portal, dst_portal, config):
    ctx.ensure_object(dict)
    ctx.obj["config"] = load_ymal(config)
    ctx.obj["src_potal"] = src_portal
    ctx.obj["dst_potal"] = dst_portal or src_portal
    ctx.obj["src_access_token"] = get_access_token(ctx.obj["config"], ctx.obj["src_potal"])
    ctx.obj["dst_access_token"] = get_access_token(ctx.obj["config"], ctx.obj["dst_potal"])


main.add_command(html.blogs)

if __name__ == "__main__":
    main()
