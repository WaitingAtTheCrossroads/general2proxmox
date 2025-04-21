#! /usr/bin/env python

"""
Migrate community.general to community.proxmox.

This is a small script for migrating Ansible Proxmox modules from
community.general to community.proxmox.  The approach is:

- Have a pre-configured list of files/directories in `community.general` that
  are desired to be kept (`config.toml`).

- Clone `community.general` repository.

- Run the pre-configured list of files through `git log --follow` to find
  historical renames.

- Pass the configured file list plus the discovered renames to `git filter-repo`
  with a `repo-filter.txt` file that gets written to disk.

- Optionally merge existing, filtered `community.general` repository
  (`main-general` branch) in to new `community.proxmox` template repo (`main`
  branch), accepting all incoming changes that may create merge conflicts.

- Optionally push to new repository.
"""

from argparse import ArgumentParser
from os import chdir, linesep, makedirs
from os.path import join
from pathlib import Path
from subprocess import run as subprocess_run
from sys import argv
from tomllib import load


class Program:
    """
    Encapsulation class to keep global scope clean.

    It's a habit.
    """

    def __init__(self, args: list[str]):
        """
        Program constructor.

        Parse command line arguments and read configuration.
        """

        parser = ArgumentParser(
            prog="general2proxmox",
            description="Migrate community.general to community.proxmox",
        )

        parser.add_argument(
            "-c",
            "--config",
            type=Path,
            help="Config file",
            default=join("cfg", "config.toml"),
        )

        parser.add_argument(
            "-v",
            "--verbose",
            help="Verbose output",
            default=False,
            action="store_true",
        )

        parser.add_argument(
            "--force",
            help="Force push to new repository",
            default=False,
            action="store_true",
        )

        parser.add_argument(
            "--merge",
            help="Merge filtered repository",
            default=False,
            action="store_true",
        )

        parser.add_argument(
            "--push",
            help="Push merged repository",
            default=False,
            action="store_true",
        )

        parser.add_argument(
            "--work-dir",
            type=Path,
            help="Working directory",
            default="work",
        )

        self.args = parser.parse_args(args)

        self.all_historical_paths: set[str] = set()

        self._read_config()

    def _add_historical_paths(self, path: str):
        """
        Track historical file names/paths.

        Use `git log --follow` to find historical paths and add them to self.
        """

        proc = self._subprocess_run(
            [
                "git",
                "log",
                "--follow",
                "--name-only",
                "--pretty=format:",
                "--no-show-signature",
                path,
            ],
            capture_output=True,
            text=True,
            check=True,
        )

        paths: set[str] = set()
        for line in proc.stdout.split(linesep):
            if line == "":
                continue

            paths.add(line)

        for path in paths:
            self.all_historical_paths.add(path)

    def _read_config(self):
        """Read configration file."""

        with open(self.args.config, "rb") as file:
            self.config = load(file)

    def _subprocess_run(self, *args, **kwargs):
        """
        Wrapper for `subprocess.run`.

        Prints command to stdout if verbose cli flag was set.
        """

        if self.args.verbose:
            print(" ".join(*args))

        return subprocess_run(*args, **kwargs)

    def run(self):
        """
        Main program logic.

        Follows process outlined above.
        """

        makedirs(self.args.work_dir, exist_ok=True)

        repo_dir: Path = self.args.work_dir.joinpath("repo")
        git_dir = repo_dir.joinpath(".git")

        if not git_dir.is_dir():
            self._subprocess_run(
                ["git", "clone", self.config["repos"]["general"], str(repo_dir)],
                check=True,
            )

        chdir(repo_dir)

        for file in self.config["repos"]["files"]:
            self._add_historical_paths(file)

        with open(join("..", "repo-filter.txt"), "w", encoding="utf-8") as file:
            for path in sorted(self.all_historical_paths):
                if path not in self.config["repos"]["false_positives"]:
                    file.write(path + linesep)

        self._subprocess_run(
            ["git", "filter-repo", "--paths-from-file", join("..", "repo-filter.txt")],
            check=True,
        )

        if self.args.merge:
            self._subprocess_run(
                [
                    "git",
                    "remote",
                    "add",
                    "upstream",
                    self.config["repos"]["proxmox_upstream"],
                ],
                check=True,
            )

            self._subprocess_run(["git", "fetch", "upstream"], check=True)

            self._subprocess_run(
                ["git", "checkout", "-b", "main-upstream", "upstream/main"], check=True
            )

            self._subprocess_run(
                ["git", "branch", "-m", "main", "main-general"], check=True
            )

            self._subprocess_run(
                ["git", "branch", "-m", "main-upstream", "main"], check=True
            )

            self._subprocess_run(
                [
                    "git",
                    "merge",
                    "main-general",
                    "--allow-unrelated-histories",
                    "--no-ff",
                    "--no-edit",
                    "--strategy-option",
                    "theirs",
                ],
                check=True,
            )

        if self.args.push:
            self._subprocess_run(
                [
                    "git",
                    "remote",
                    "add",
                    "origin",
                    self.config["repos"]["proxmox_origin"],
                ],
                check=True,
            )

            cmd: list[str] = [
                "git",
                "push",
                "origin",
            ]

            args: list[str] = [
                '--branches',
                '--tags',
                '--prune',
            ]

            for arg in args:
                this_cmd = cmd.copy()
                this_cmd.append(arg)

                if self.args.force:
                    this_cmd.append("--force")

                self._subprocess_run(this_cmd, check=True)


def main():
    """Run program."""

    Program(argv[1:]).run()


if __name__ == "__main__":
    main()
