import click

from cli import job_applications


@click.group()
def main() -> None:
    """
    CLI entry point.
    """
    pass


@main.command()
def ping() -> None:
    click.echo(click.style("pong!", fg="green"))

main.add_command(job_applications.main, name="process_job_applications")


if __name__ == "__main__":
    main()
