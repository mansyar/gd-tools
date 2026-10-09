"""The ``completion`` command.

Defined via a factory because the command body needs a reference to
the root CLI group to generate its completion script.
"""

import click
from click.shell_completion import get_completion_class


def create_completion_command(cli_group: click.Group) -> click.Command:
    """Build the ``completion`` command bound to *cli_group*.

    Args:
        cli_group: The root Click group whose commands and options the
            generated completion script should describe.

    Returns:
        The Click command implementing ``gd-tools completion SHELL``.
    """

    @click.command()
    @click.argument(
        "shell",
        type=click.Choice(["bash", "zsh", "fish", "powershell"]),
    )
    def completion(shell: str) -> None:
        """Generate shell completion scripts for gd-tools.

        Outputs the completion script for the specified shell to stdout.
        Source the script in your shell's configuration file to enable
        tab completion for gd-tools commands and options.

        \b
        Supported shells:
          bash       Generate bash completion script
          zsh        Generate zsh completion script
          fish       Generate fish completion script
          powershell Generate PowerShell completion script

        \b
        Examples:
          eval "$(gd-tools completion bash)"
          gd-tools completion zsh > ~/.zsh/completions/_gd-tools
          gd-tools completion fish > ~/.config/fish/completions/gd-tools.fish
          gd-tools completion powershell | Out-String | Add-Content $PROFILE
        """
        comp_class = get_completion_class(shell)
        if comp_class is None:  # pragma: no cover
            raise click.UsageError(f"Unsupported shell: {shell}")
        prog_name = "gd-tools"
        complete_var = f"_{prog_name.upper().replace('-', '_')}_COMPLETE"
        comp = comp_class(
            cli=cli_group,
            ctx_args={},
            prog_name=prog_name,
            complete_var=complete_var,
        )
        click.echo(comp.source())

    return completion
