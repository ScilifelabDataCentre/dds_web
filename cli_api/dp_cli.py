"""module docstring"""

import click

@click.command()
@click.option('--file', default="", help="Files to be uploaded.")

def upload_files(file):
    """function docstring"""

    click.echo(file)


def main():
    upload_files()


if __name__ == '__main__':
    main()
