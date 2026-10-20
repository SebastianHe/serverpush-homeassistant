# Publishing ServerPush for Home Assistant

## Current review

The local review passed all 72 integration tests with 100% line coverage of the integration code, Ruff linting, and the formatting check. Tests mock HTTP and do not demonstrate a successful delivery through the live ServerPush service.

The repository uses the HACS integration layout, contains one integration, includes 256 px and 512 px brand icons, and declares version `0.1.0`. `hacs.json` requires Home Assistant 2026.10.0 or newer. English and German setup translations are included.

Publication is **not complete**. The owner confirmed `https://github.com/SebastianHe/serverpush-homeassistant` and selected the MIT license, included in `LICENSE`. This directory is not yet a Git checkout, and the GitHub validation jobs must pass before release.

A pattern scan of the 20 source, configuration, and documentation text files available during review found no matching private keys, GitHub tokens, AWS access key IDs, or literal ServerPush webhook URLs containing long tokens. This is a limited pattern check; no Git history was available to review.

## Before the first public release

- Use the confirmed repository address: `https://github.com/SebastianHe/serverpush-homeassistant`. If it changes, update the repository URLs and HACS button parameters in both READMEs, and `documentation`, `issue_tracker`, and `codeowners` in the integration manifest.
- Keep the included MIT `LICENSE` file with the source and verify the right to distribute the source and brand assets.
- Initialize a Git repository and review the staged files before pushing. `.gitignore` excludes virtual environments, caches, coverage, build output, and macOS metadata. This review cannot check Git history because none exists in this directory.
- Create the public GitHub repository with Issues enabled. Suggested description: `Send Home Assistant notifications to ServerPush chats with four severity levels.` Suggested topics: `home-assistant`, `hacs`, `custom-integration`, `notifications`, `serverpush`.
- Push the source and let the Tests and Validate integration workflows pass. HACS validation checks GitHub metadata as well as files, so it cannot be completed against this unpublished local directory. Do not ignore license, brands, or metadata checks to obtain a passing result.
- Test the HACS button against the actual repository, download through HACS into a Home Assistant instance running 2026.10 or newer, restart, and open setup using the configuration button.
- Use a dedicated test chat to validate a token and send one notification through `notify.send_message`. Check all four severity entities, token replacement, and removal of the integration. Mocked tests already cover these flows; the manual check verifies packaging and live-service compatibility.

## Releases and updates

1. Update `custom_components/serverpush/manifest.json` with the intended version and run the checks documented in the README.
2. Publish a GitHub release with a matching version tag, such as `v0.1.0`, and release notes. HACS can install from the default branch without a release, but versioned releases provide a clearer update path.
3. HACS currently downloads the integration from repository sources. `zip_release` is not enabled; the local `dist/` ZIP is ignored and is not required for installation.
4. Check that HACS offers the release and installs the expected files.

A public custom repository can be added directly to HACS. Inclusion in the default catalog is a separate submission and must not be claimed before acceptance.

References: [HACS integration requirements](https://www.hacs.xyz/docs/publish/integration/), [general publication requirements](https://www.hacs.xyz/docs/publish/start/), [HACS validation action](https://www.hacs.xyz/docs/publish/action/).
