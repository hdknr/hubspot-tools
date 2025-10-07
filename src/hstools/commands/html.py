import click
import json
import os
import re
from mimetypes import guess_type
from pathlib import Path
from urllib.parse import unquote, urlparse, urlsplit

import click
from bs4 import BeautifulSoup as Soup
from dotenv import load_dotenv

@click.group()
@click.pass_context
def html(ctx):
    ctx.ensure_object(dict)
    load_dotenv()


def generate_new_path(original_path):
    """
    オリジナルのパスを新しいパターンに置換する関数。
    """
    original_path = str((Path("/") / original_path).resolve())
    THEME = os.environ["HUBSPOT_FOLDER"]
    public_path = f"{{{{get_asset_url('/{THEME}{original_path}') }}}}"
    return public_path


def change_assert_url_tag(asset_tag, profile=None):
    tag_name = asset_tag.name
    attr_name = "href" if tag_name in ["a", "link"] else "src"
    original_src = asset_tag.get(attr_name)

    if not original_src:
        return

    if original_src.startswith("http"):
        # 絶対パスは変換しない(外部の可能性)
        parsed = urlparse(original_src)
        if parsed.netloc == os.environ.get("TARGET_CNAME", ""):
            original_src = parsed.path

        else:
            return

    changed = change_anchor_url_rule(original_src, profile=profile)

    original_src = changed

    mt, _ = guess_type(original_src)
    if not mt or mt in ["text/html"]:
        asset_tag[attr_name] = original_src
        return

    new_src = generate_new_path(original_src)

    asset_tag[attr_name] = new_src
    click.echo(f"置き換え:  {tag_name}.{attr_name}: {original_src} -> {new_src}")


def change_asset_url(soup, profile=None):
    img_tags = soup.find_all(["img", "script", "link", "a"])

    if not img_tags:
        click.echo("<img>タグが見つかりませんでした。")
        return

    _ = [change_assert_url_tag(tag, profile=profile) for tag in img_tags]



@html.command()
@click.argument("input_file", type=click.Path(exists=True))
@click.option("--profile", "-p", default=None)
@click.option("--output_file", "-o", type=click.Path(), default=None)
@click.pass_context
def asset_url(ctx, input_file, profile, output_file):
    """
    HTMLファイル内の<img>タグのsrc属性のパスを一括置換するコマンドラインツール。

    INPUT_FILE: 読み込むHTMLファイルのパス。
    OUTPUT_FILE: 出力するHTMLファイルのパス。
    """
    if not output_file:
        path = Path(input_file)
        output_file = str(path.parent / f"out.{path.name}")

    try:
        profile_data = load_profile(profile)
        click.echo(f'ファイル "{input_file}" を読み込んでいます...')
        with open(input_file, encoding="utf-8") as f:
            soup = Soup(f, "html.parser")

        change_asset_url(soup, profile=profile_data)

        click.echo(f'修正されたHTMLを "{output_file}" に書き込みます...')
        with open(output_file, "w", encoding="utf-8") as f:
            f.write(str(soup))

        click.echo(
            f'処理が完了しました。修正されたHTMLは "{output_file}" に保存されました。'
        )

    except Exception as e:
        click.echo(f"エラーが発生しました: {e}", err=True)


@html.command()
@click.argument("directory", type=click.Path(exists=True))
@click.pass_context
def strip_qstr(ctx, directory):
    """
    指定されたディレクトリ内のファイル名からクエリ文字列を削除します。
    例: style.css?ver=6.7.3 -> style.css

    Args:
        directory (str): 処理対象のディレクトリパス
    """
    for root, _dirs, files in os.walk(directory):
        for filename in files:
            # 正規表現でファイル名にクエリ文字列が含まれているかチェック
            # 例: 'style.css?ver=6.7.3.css' を 'style.css.css' に
            # ※ wgetの保存方法によっては末尾に`.css`が追加される場合があるため、この例ではその可能性も考慮
            if "?" in filename:
                original_filepath = os.path.join(root, filename)
                # `?`以降の文字列を削除
                new_filename = re.sub(r"\?.*", "", filename)

                # wgetで保存されたファイルは、`.css?ver=6.7.3` のようなクエリ文字列がそのままファイル名に含まれるため、
                # 元の拡張子(`.css`や`.js`)が複数になることがある。
                # 例: `style.css?ver=6.7.3.css` -> `style.css.css`
                # このようなファイル名の場合は、最後の`.css`のみを残すように修正
                if new_filename.endswith(".css.css"):
                    new_filename = new_filename.replace(".css.css", ".css")
                elif new_filename.endswith(".js.js"):
                    new_filename = new_filename.replace(".js.js", ".js")

                new_filepath = os.path.join(root, new_filename)

                # ファイル名を変更
                try:
                    os.rename(original_filepath, new_filepath)
                    print(f"Renamed: {original_filepath} -> {new_filepath}")
                except OSError as e:
                    print(f"Error renaming {original_filepath}: {e}")


@html.command()
@click.argument("src")
@click.pass_context
def hs_url(ctx, src):
    """アセットURLを生成"""
    THEME = os.environ["HUBSPOT_FOLDER"]
    dst = f"{{{{ get_asset_url('/{THEME}/{src}') }}}}"
    print(dst)


def change_anchor_url_rule(href, profile: dict):
    url = unquote(href)
    obj = urlsplit(url)
    path = str((Path("/") / obj.path).resolve())

    if href.startswith("mailto"):
        return href

    mtype, _ = guess_type(path)
    if mtype and mtype.startswith("image"):
        return generate_new_path(path)

    rules = profile.get("rules", None) or []
    for rule in rules:
        if re.search(rf"{rule[0]}", path):
            path = re.sub(rf"{rule[0]}", rf"{rule[1]}", path)
            break
    if obj.query:
        path = path + f"?{obj.query}"

    return path  # , obj.query


def change_anchor_url_tag(asset_tag, profile: dict):
    tag_name = asset_tag.name
    attr_name = "href"
    original_src = asset_tag.get(attr_name)

    if not original_src:
        return

    if original_src.startswith("http"):
        # 絶対パスは変換しない(外部の可能性)
        return

    new_src = change_anchor_url_rule(original_src, profile)

    asset_tag[attr_name] = new_src

    click.echo(f"href変更:  {tag_name}.{attr_name}: {original_src} -> {new_src}")


def change_anchor_url(soup: Soup, profile: dict):
    elms = soup.find_all(["a"])

    if not elms:
        click.echo("<a>タグが見つかりませんでした。")
        return

    _ = [change_anchor_url_tag(elm, profile) for elm in elms]


def extract_elements(soup: Soup, profile: dict):
    """コンテンツを抜き出して(src)アセットURLの変換を行う
    - 不要な要素の削除(drops)
    """
    src = soup.select_one(profile["src"])
    drops = profile.get("drops", None) or []

    for i in drops:
        elm = src.select_one(i)
        elm and elm.extract()

    change_asset_url(src, profile)
    # change_anchor_url(src, profile)

    return src


def load_profile(profile):
    if not profile:
        return {}
    path = Path(profile)
    if not path.is_file or path.suffix != ".json":
        return {}

    profile_data = json.load(open(profile))
    return profile_data


@html.command()
@click.argument("src_path")
@click.option("--profile", "-p", default=None)
@click.option("--output_file", "-o", type=click.Path(), default=None)
@click.pass_context
def extract(ctx, src_path, profile, output_file):
    """コンテンツ抜き出し"""
    profile = profile or os.environ.get("EXTRACT_PROFILE", None)
    src = Path(src_path)
    if not src.is_file or src.suffix != ".html":
        print("source error")
        return

    path = Path(profile)
    if not path.is_file or path.suffix != ".json":
        print("profile error")
        return

    profile_data = load_profile(profile)

    if not output_file:
        path = Path(src_path)
        output_file = str(path.parent / f"out.{path.name}")

    with open(src_path, encoding="utf-8") as f:
        soup = Soup(f, "html.parser")
        res = extract_elements(soup, profile_data)
        with open(output_file, "w", encoding="utf-8") as f:
            f.write(str(res))
